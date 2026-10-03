"""Concurrency defaults for GPT API calls (``GPT_*`` / OpenAI-compatible gateway)."""

# Provider-enforced maximum in-flight requests per account (observed: 429 above this).
GPT_API_CONCURRENCY_LIMIT = 5

# Default for QuanBench+ and related experiments: one below the hard limit.
GPT_API_MAX_WORKERS_DEFAULT = 4
