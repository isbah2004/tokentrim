"""Phase 1 sanity check: confirm Model Studio credentials and connectivity.

Run this AFTER exporting DASHSCOPE_API_KEY (or setting it in .env). It is the
"hello world" of the build — if it prints a real response, the plumbing works
and you can move on to the core layers.

    python scripts/hello_qwen.py

This is the only script that talks to the live API during Phase 1; the core
layers in later phases are all unit-testable offline.
"""
import os
import sys

# Allow running from the repo root without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config


def main() -> int:
    if not config.DASHSCOPE_API_KEY:
        print("DASHSCOPE_API_KEY is not set. Run: export DASHSCOPE_API_KEY=sk-xxx")
        return 1

    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        print("The 'openai' package is not installed. Run: pip install -U openai")
        return 1

    client = OpenAI(api_key=config.DASHSCOPE_API_KEY, base_url=config.BASE_URL)
    completion = client.chat.completions.create(
        model=config.MODEL_PLUS,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who are you?"},
        ],
    )
    print(completion.choices[0].message.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
