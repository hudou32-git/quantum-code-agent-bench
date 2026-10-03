from pass_at_k_pipeline.cirq_pip.paths import CIRQ_JSONL
from pass_at_k_pipeline.pennylane_pip.paths import PENNYLANE_JSONL
from pass_at_k_pipeline.qiskit_pip.paths import QISKIT_JSONL
from pass_at_k_pipeline.pennylane_pip.paths import (
    MODEL_RESPONSES_DIR as MODEL_RESPONSES_DIR_PENNYLANE,
)
from pass_at_k_pipeline.cirq_pip.paths import (
    MODEL_RESPONSES_DIR as MODEL_RESPONSES_DIR_CIRQ,
)
from pass_at_k_pipeline.qiskit_pip.paths import (
    MODEL_RESPONSES_DIR as MODEL_RESPONSES_DIR_QISKIT,
)
import time
from typing import Any, Dict, List
from utils.parse_prompt import parse_prompt
from utils.get_function_signature_from_prompt import get_function_signature_from_prompt
from utils.read_jsonl import read_jsonl
from utils.parse_response import parse_response
from utils.chat_payload import normalize_chat_completions_url, sanitize_chat_payload_for_url
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dotenv import load_dotenv
import os
import json
import argparse
from pass_at_k_pipeline.defaults import DEFAULT_MODELS
from utils.gpt_concurrency import GPT_API_MAX_WORKERS_DEFAULT

load_dotenv()

DEFAULT_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/v1/chat/completions"


def send_request(request):
    api_key = os.getenv("API_KEY")
    model = request.get("model")
    print("Sending request to", model)
    url = normalize_chat_completions_url(
        os.getenv("CHAT_COMPLETIONS_URL", DEFAULT_CHAT_COMPLETIONS_URL).strip()
    )
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = request.get("messages") or []
    chat_completion = ""
    if len(messages) > 1 and isinstance(messages[1], dict):
        chat_completion = messages[1].get("content") or ""
    try:
        payload = sanitize_chat_payload_for_url(url, request)
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        if response.status_code != 200:
            err_body = response.text[:4000]
            print(
                f"API non-200 for model={model}: status={response.status_code} body[:500]={err_body[:500]!r}"
            )
            return (
                {
                    "error": {
                        "status_code": response.status_code,
                        "body": err_body,
                    }
                },
                chat_completion,
            )
        data = response.json()
        return data, chat_completion
    except Exception as e:
        print("ERROR SENDING REQUEST")
        print(e)
        return ({"error": {"message": str(e)}}, chat_completion)


def parse_requests(json_path: str, models: list):
    tasks = read_jsonl(json_path)
    requests = []
    tasks_info = []
    for model in models:
        for task in tasks:
            chat_completion_part = get_function_signature_from_prompt(
                task.get("complete_prompt")
            )
            requests.append(
                parse_prompt(
                    task.get("complete_prompt"),
                    chat_completion_part,
                    model,
                    n=1,
                    prefill=False,
                )
            )
            tasks_info.append(
                {
                    "task_id": task.get("task_id"),
                    "entry_point": task.get("entry_point"),
                    "category": task.get("category"),
                    "model": model,
                }
            )

    return requests, tasks_info


def process_single_task_pass_k(args):
    """
    Process ONE (task, version) sample.
    Returns (task_index, version, enriched_result).
    """
    task_index, request, task_info, version, pass_k = args
    entry_point = task_info.get("entry_point")
    single_request = {k: v for k, v in request.items() if k != "n"}
    single_request.setdefault("temperature", 0.8)
    if pass_k > 1:
        single_request["temperature"] = 0.8
    try:
        raw_response = send_request(single_request)
        parsed_response = parse_response(raw_response, entry_point)

        enriched_result = {
            **task_info,  # task_id, entry_point, category, model, ...
            **parsed_response,
            "version": version,
            # API may omit or null ``model`` in the JSON body; keep CLI / task model for saves.
            "model": task_info.get("model"),
        }
        return task_index, version, enriched_result
    except Exception as exc:
        print(
            f"Request task {task_info.get('task_id')} v{version} generated an exception: {exc}"
        )
        error_result = {
            "id": f"error-{int(time.time())}-{task_index}-v{version}",
            "choices": [
                {
                    "finish_reason": "error",
                    "native_finish_reason": "error",
                    "message": {
                        "role": "assistant",
                        "content": f"Error: {str(exc)}",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "code": "",
            **task_info,
            "version": version,
        }
        return task_index, version, error_result


def process_requests_pass_k(
    requests, tasks_info, pass_k, max_workers: int = GPT_API_MAX_WORKERS_DEFAULT
):
    """
    Fully-parallel pass@k:
    Submits len(requests) * pass_k independent jobs to the thread pool.
    in deterministic order: task i occupies [i*pass_k ... i*pass_k + pass_k-1].
    """
    total_tasks = len(requests)
    total_calls = total_tasks * pass_k
    completed = 0
    print(
        f"   Sending {total_calls} requests with {max_workers} concurrent workers (pass@{pass_k})..."
    )
    results = [None] * total_calls
    all_args = []
    for i, (req, info) in enumerate(zip(requests, tasks_info)):
        for v in range(1, pass_k + 1):
            all_args.append((i, req, info, v, pass_k))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_key = {
            executor.submit(process_single_task_pass_k, args): (args[0], args[3])
            for args in all_args
        }

        for future in as_completed(future_to_key):
            task_index, version = future_to_key[future]
            out_index = task_index * pass_k + (version - 1)

            try:
                _, _, result = future.result()
                results[out_index] = result
            except Exception as exc:
                print(
                    f"Request task {task_index} v{version} generated an exception: {exc}"
                )
                results[out_index] = {
                    "id": f"error-{int(time.time())}-{task_index}-v{version}",
                    "choices": [
                        {
                            "finish_reason": "error",
                            "native_finish_reason": "error",
                            "message": {
                                "role": "assistant",
                                "content": f"Error: {str(exc)}",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "code": "",
                    **tasks_info[task_index],
                    "version": version,
                }

            completed += 1
            if completed % 10 == 0:
                print(
                    f"   Progress: {completed}/{total_calls} ({completed / total_calls * 100:.1f}%)"
                )

            time.sleep(0.01)

    print(f"\n   ✅ Completed all {total_calls} requests (pass@{pass_k})")
    return results


def get_jsonl_path(framework: str):
    if framework == "cirq":
        return CIRQ_JSONL
    elif framework == "pennylane":
        return PENNYLANE_JSONL
    else:
        return QISKIT_JSONL


def get_model_reponses_dir(framework: str):
    if framework == "cirq":
        return MODEL_RESPONSES_DIR_CIRQ
    elif framework == "pennylane":
        return MODEL_RESPONSES_DIR_PENNYLANE
    else:
        return MODEL_RESPONSES_DIR_QISKIT


def main(
    models: list,
    framework: str,
    pass_k: int = 1,
    max_workers: int = GPT_API_MAX_WORKERS_DEFAULT,
):
    all_results: Dict[str, List[Dict[str, Any]]] = {f"{framework}": []}
    jsonl_path = get_jsonl_path(framework=framework)
    model_response_dir = get_model_reponses_dir(framework=framework)
    print("Starting API requests...")
    requestss, tasks_info = parse_requests(jsonl_path, models)

    print(f"   Generated {len(requestss)} requests across {len(models)} models")
    results = process_requests_pass_k(requestss, tasks_info, pass_k, max_workers)

    all_results[f"{framework}"] = results
    print(f"Completed {len(results)} responses")

    # Ensure the directory exists before saving
    print(f"Saving results to file: {model_response_dir}...")
    model_response_dir.mkdir(parents=True, exist_ok=True)

    for model in models:
        model_name = model.replace("/", "_")
        model_results = [r for r in results if r.get("model") == model]
        output_file = model_response_dir / f"{model_name}_{framework}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(model_results, f, indent=2, ensure_ascii=False)
        print(f"   Saved {len(model_results)} results to {output_file}")

    total_results = len(results)
    print(f"All done! Saved {total_results} total responses")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run LLM evaluation on quantum computing tasks"
    )
    parser.add_argument("models", nargs="*", help="Model names to evaluate")
    parser.add_argument(
        "--framework",
        type=str,
        default="cirq",
        choices=["cirq", "pennylane", "qiskit"],
        help="Framework to use: cirq, pennylane, or qiskit (default: cirq)",
    )
    parser.add_argument(
        "--pass_k",
        type=int,
        default=1,
        help="Number of samples for pass@k evaluation (default: 1)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=GPT_API_MAX_WORKERS_DEFAULT,
        help=(
            "Concurrent API requests (default: %(default)s). "
            "GPT gateway hard limit is 5; use 4 for experiments."
        ),
    )
    args = parser.parse_args()
    models = args.models if args.models else DEFAULT_MODELS
    main(models, args.framework, args.pass_k, args.max_workers)
