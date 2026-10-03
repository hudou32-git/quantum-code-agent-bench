import re


def extract_code_from_markdown(text: str, entry_point: str) -> str:
    """Extract Python code from markdown code blocks if present."""
    if not text:
        return ""
    # Try to find ```python ... ``` blocks first
    python_blocks = re.findall(r"```python\s*(.*?)```", text, re.DOTALL)
    if python_blocks:
        # Find the block containing the entry point function
        for block in python_blocks:
            if f"def {entry_point}" in block:
                return block.strip()
        # If no block has the entry point, return the first block
        return python_blocks[0].strip()

    # Try generic ``` ... ``` blocks
    generic_blocks = re.findall(r"```\s*(.*?)```", text, re.DOTALL)
    if generic_blocks:
        for block in generic_blocks:
            if f"def {entry_point}" in block:
                return block.strip()
        return generic_blocks[0].strip()

    return text


def parse_response(args, entry_point):
    """Parse single response (first choice only)."""
    if isinstance(args, (list, tuple)) and len(args) >= 2:
        response, chat_completion = args[0], args[1]
    elif isinstance(args, dict):
        response, chat_completion = args, ""
    else:
        response, chat_completion = {}, ""

    out: dict = {}
    out["model"] = response.get("model")
    usage = response.get("usage") or {}

    out["usage"] = usage
    out["prompt_tokens"] = usage.get("prompt_tokens")
    out["completion_tokens"] = usage.get("completion_tokens")
    out["total_tokens"] = usage.get("total_tokens")
    cdet = usage.get("completion_tokens_details") or {}
    pdet = usage.get("prompt_tokens_details") or {}

    out["reasoning_tokens"] = cdet.get("reasoning_tokens")
    out["accepted_prediction_tokens"] = cdet.get("accepted_prediction_tokens")
    out["rejected_prediction_tokens"] = cdet.get("rejected_prediction_tokens")
    out["cached_tokens"] = pdet.get("cached_tokens")
    out["cache_write_tokens"] = pdet.get("cache_write_tokens")

    def _fail_code(note: str) -> dict:
        out["code"] = ""
        out["api_error"] = note[:4000]
        return out

    choices = response.get("choices")
    if response.get("error") and not choices:
        err = response["error"]
        if isinstance(err, dict):
            note = err.get("body") or err.get("message") or str(err)
        else:
            note = str(err)
        return _fail_code(f"API error: {note}")

    if not choices:
        return _fail_code(f"No choices in response keys={list(response.keys())}")

    first = choices[0] if isinstance(choices[0], dict) else {}
    msg = first.get("message") if isinstance(first.get("message"), dict) else {}
    raw_content = msg.get("content")
    if raw_content is None:
        raw_content = ""
    if not str(raw_content).strip():
        # DeepSeek thinking mode: final answer may be empty while reasoning is populated.
        rc = msg.get("reasoning_content")
        if rc:
            raw_content = str(rc)

    code = extract_code_from_markdown(raw_content, entry_point)

    if ("def " + entry_point) not in code:
        print("This is a chat completion model!")
        code = (chat_completion or "") + code
    out["code"] = code
    return out
