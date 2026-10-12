import os
import re
import sys
import time
from pathlib import Path

from openai import OpenAI


def sanitize_log(text: str) -> str:
    patterns = [
        r"sk-[A-Za-z0-9_-]+",
        r"ghp_[A-Za-z0-9]+",
        r"github_pat_[A-Za-z0-9_]+",
        r"Bearer\s+[A-Za-z0-9._-]+",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)

    return text


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/ai_diagnose.py <log_file>")
        sys.exit(1)

    log_path = Path(sys.argv[1])

    if not log_path.exists():
        print(f"Log file does not exist: {log_path}")
        sys.exit(1)

    log_content = sanitize_log(
        log_path.read_text(encoding="utf-8", errors="replace")
    )

    prompt = f"""
You are assisting with diagnosis of a failed CI/CD deployment of a Flask
application running in Docker and deployed with GitHub Actions.

Analyze only the information present in the log.

Return the answer in exactly this structure:

CAUSE:
A short explanation of the most likely root cause.

FIX:
Concrete steps or configuration changes that should resolve the problem.

CONFIDENCE:
One of: LOW, MEDIUM, HIGH.

RISK:
Mention whether the proposed fix could introduce a deployment or security risk.

DEPLOYMENT LOG:
{log_content}
"""

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    started = time.perf_counter()

    response = client.responses.create(
        model="gpt-6-luna",
        input=prompt,
    )

    elapsed = time.perf_counter() - started

    diagnosis = response.output_text

    print("\n===== AI DEPLOYMENT DIAGNOSIS =====\n")
    print(diagnosis)
    print("\n===================================")
    print(f"AI response time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()