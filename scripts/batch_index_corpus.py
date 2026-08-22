"""Batch-embed a corpus into the pgvector cache — the off-the-hot-path lever.

Batch calls are billed at 50% off but are asynchronous and cannot combine with
context-cache discounts, so they belong in indexing/backfill jobs, never on the
live /chat path. Use this to pre-embed an FAQ/knowledge base before a demo.

Build a JSONL file where each line is a standard embeddings request body, then:

    python scripts/batch_index_corpus.py corpus_batch.jsonl

Requires the `openai` package and DASHSCOPE_API_KEY.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/batch_index_corpus.py <corpus_batch.jsonl>")
        return 2
    batch_path = Path(argv[1])
    if not batch_path.exists():
        print(f"file not found: {batch_path}")
        return 1
    if not config.DASHSCOPE_API_KEY:
        print("DASHSCOPE_API_KEY is not set.")
        return 1

    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        print("The 'openai' package is not installed. Run: pip install -U openai")
        return 1

    client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.BASE_URL)

    file_object = client.files.create(file=batch_path, purpose="batch")
    print("uploaded:", file_object.model_dump_json())

    batch = client.batches.create(
        input_file_id=file_object.id,
        endpoint="/v1/embeddings",
        completion_window="24h",
    )
    print("batch submitted:", batch.id)
    print("Poll with: client.batches.retrieve(batch_id) until status == 'completed',")
    print("then download the output file and INSERT the vectors into tokentrim_cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
