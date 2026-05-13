#!/usr/bin/env python3
"""
summarize_chats.py — Weekly review of Magpie chatbot conversations.

Reads the chat_log.jsonl, feeds the past 7 days (or all-time if smaller) to
Claude, and prints a markdown summary you can read in 5 minutes:

  - Top recurring questions
  - Suggested additions to chatbot_knowledge.md
  - Any worrying redaction violations or near-misses
  - High-volume topics that hint at product gaps

Run:
  cd /path/to/magpie-chatbot-backend   (or anywhere with the log file)
  python summarize_chats.py [--days 7] [--log chat_log.jsonl]

Env:
  ANTHROPIC_API_KEY — required for the summary call

Usage tip: schedule this as a weekly cron, or run manually whenever you want
to review what visitors are asking.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic", file=sys.stderr)
    sys.exit(1)

MODEL = "claude-haiku-4-5"


def load_recent_turns(log_path: Path, days: int):
    """Yield log entries from the past `days` days."""
    if not log_path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    turns = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts = datetime.fromisoformat(entry["ts"])
            if ts >= cutoff:
                turns.append(entry)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return turns


SUMMARY_PROMPT = """You are an analyst reviewing one week of chatbot conversations
from magpiestudios.app — the Magpie Studios product site.

Below are visitor questions and the bot's replies. Produce a concise markdown
report with these sections:

1. **Top 5 recurring questions** — group similar phrasings; for each, give a
   one-line example and count.
2. **Questions the bot answered poorly or vaguely** — flag specific cases
   where the bot deflected when it could have given a real answer, or where
   the reply could be sharper.
3. **Suggested additions to chatbot_knowledge.md** — concrete bullet points
   the studio could paste into the knowledge file to make next week's
   answers better.
4. **Redaction near-misses or violations** — any cases where the bot
   revealed too much (real names, internal info, competitive details), or
   where a visitor tried hard to extract it.
5. **Product or content signals** — what are visitors curious about that
   isn't covered well by the current site? Hint at potential new pages or
   product features.

Be specific. Cite actual visitor questions. Keep total length under 600
words.

----- CONVERSATIONS -----
{turns}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--days", type=int, default=7,
                        help="Window in days (default 7)")
    parser.add_argument("--log", default="chat_log.jsonl",
                        help="Path to JSONL log (default ./chat_log.jsonl)")
    parser.add_argument("--max-turns", type=int, default=500,
                        help="Cap to keep prompt size reasonable")
    args = parser.parse_args()

    log_path = Path(args.log)
    turns = load_recent_turns(log_path, args.days)

    if not turns:
        print(f"No turns found in last {args.days} days at {log_path}.")
        return 0

    if len(turns) > args.max_turns:
        print(f"# {len(turns)} turns found — sampling latest {args.max_turns}",
              file=sys.stderr)
        turns = turns[-args.max_turns:]

    # Format for the prompt
    formatted = []
    for t in turns:
        formatted.append(f"[{t.get('ts', '?')}]")
        formatted.append(f"  visitor: {t.get('user', '').strip()}")
        formatted.append(f"  bot:     {t.get('assistant', '').strip()}")
        formatted.append("")
    turns_str = "\n".join(formatted)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    if not client.api_key:
        print("ERROR: set ANTHROPIC_API_KEY in env", file=sys.stderr)
        return 1

    print(f"# Magpie chatbot weekly summary ({args.days}-day window)")
    print(f"# {len(turns)} turns analyzed")
    print(f"# Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(turns=turns_str)}],
    )
    print(response.content[0].text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
