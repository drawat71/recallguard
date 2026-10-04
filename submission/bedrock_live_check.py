"""One-shot Bedrock check for the current local RecallGuard run.

Reads the current workflow facts over local MCP, makes exactly one Converse
request, and prints only the explanation and elapsed inference-call time.
"""
import asyncio
import json
import sys
from time import perf_counter

from ui.bridge import call_tool
from ui.aws.bedrock_explanation import explain, facts_from_events


async def load_facts(run_id):
    case = await call_tool("get_case", {"run_id": run_id})
    feed = await call_tool("get_events", {"run_id": run_id, "after_seq": -1})
    if "error" in case or "error" in feed:
        raise RuntimeError("That run is unavailable. Start a fresh local case and retry.")
    if case.get("state") != feed.get("state") or case.get("event_count") != len(feed.get("events", [])):
        raise RuntimeError("The case changed while preparing the request. Refresh and retry.")
    return facts_from_events(feed["events"])


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: .venv/bin/python submission/bedrock_live_check.py WF-0001")
    try:
        facts = asyncio.run(load_facts(sys.argv[1]))
        start = perf_counter()
        answer = explain(facts)
        elapsed_ms = round((perf_counter() - start) * 1000)
        print(json.dumps({"status": "success", "latency_ms": elapsed_ms, "explanation": answer}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "fallback", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
