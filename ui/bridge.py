"""Local UI adapter. Only forwards the six frozen lifecycle tools over real MCP HTTP."""
import asyncio
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

os.environ.setdefault("FASTMCP_CHECK_FOR_UPDATES", "off")
from fastmcp import Client

PUBLIC = Path(__file__).parent / "public"
MCP_URL = "http://127.0.0.1:8000/mcp/"
CONTRACT = {
    "start_case": ({"product_key"}, set()),
    "submit_verification": ({"run_id"}, {"serial", "user_attested"}),
    "approve_action": ({"run_id", "action_id"}, set()),
    "deny_action": ({"run_id"}, set()),
    "get_case": ({"run_id"}, set()),
    "get_events": ({"run_id"}, {"after_seq"}),
}


def validate_explanation_request(args):
    if not isinstance(args, dict) or set(args) != {"run_id"} or not isinstance(args["run_id"], str) or not args["run_id"].strip():
        raise ValueError("Expected only the current run_id")


def validate(tool, args):
    if tool not in CONTRACT or not isinstance(args, dict):
        raise ValueError("Unsupported lifecycle request")
    required, optional = CONTRACT[tool]
    if not required <= args.keys() or args.keys() - required - optional:
        raise ValueError("Arguments do not match the frozen lifecycle contract")
    for key, value in args.items():
        if key == "after_seq":
            valid = type(value) is int and value >= -1
        elif key == "user_attested":
            valid = type(value) is bool
        elif key == "serial":
            valid = value is None or isinstance(value, str)
        else:
            valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            raise ValueError(f"Invalid {key}")


async def call_tool(tool, args):
    async with Client(MCP_URL, timeout=90) as client:
        result = await client.call_tool(tool, args)
        return json.loads(result.content[0].text)


def _bedrock_imports():
    # `python ui/bridge.py` places ui/ on sys.path; tests import ui.bridge from the repo root.
    if __package__:
        from .aws.bedrock_explanation import BedrockExplanationError, explain, facts_from_events
    else:
        from aws.bedrock_explanation import BedrockExplanationError, explain, facts_from_events
    return BedrockExplanationError, explain, facts_from_events


async def explain_case(run_id):
    BedrockExplanationError, explain, facts_from_events = _bedrock_imports()
    snapshot = await call_tool("get_case", {"run_id": run_id})
    events = await call_tool("get_events", {"run_id": run_id, "after_seq": -1})
    if "error" in snapshot or "error" in events:
        raise ValueError("This workflow case is no longer available.")
    if snapshot["state"] != events["state"] or snapshot["event_count"] != len(events["events"]):
        raise ValueError("The case changed. Refresh it before asking for an explanation.")
    facts = facts_from_events(events["events"])
    return explain(facts)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        super().end_headers()

    def respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Local-only app: prevent unrelated web pages from invoking device actions.
        host = self.headers.get("Host", "")
        if host not in {"127.0.0.1:3000", "localhost:3000"}:
            return self.respond(403, {"error": "Invalid local host"})
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{host}":
            return self.respond(403, {"error": "Cross-origin requests are not allowed"})
        if self.headers.get_content_type() != "application/json":
            return self.respond(415, {"error": "JSON required"})
        tool = urlsplit(self.path).path.removeprefix("/api/")
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 16384:
                raise ValueError("Invalid request size")
            args = json.loads(self.rfile.read(length))
            if tool == "explain_evidence":
                validate_explanation_request(args)
            else:
                validate(tool, args)
        except (ValueError, TypeError) as exc:
            return self.respond(400, {"error": str(exc)})
        try:
            if tool == "explain_evidence":
                BedrockExplanationError, _, _ = _bedrock_imports()
                try:
                    explanation = asyncio.run(explain_case(args["run_id"]))
                except BedrockExplanationError as exc:
                    return self.respond(503, {"error": str(exc)})
                except Exception:
                    return self.respond(503, {"error": "Recall evidence could not be prepared for Bedrock. The workflow case is unchanged; refresh the case and try again."})
                self.respond(200, {"provider": "Amazon Bedrock", "explanation": explanation})
                return
            data = asyncio.run(call_tool(tool, args))
            self.respond(409 if "error" in data else 200, data)
        except Exception as exc:
            if tool == "explain_evidence":
                return self.respond(503, {"error": f"Optional Bedrock explanation unavailable ({type(exc).__name__}). Your workflow case is unchanged."})
            self.respond(502, {"error": "MCP request failed. Check the backend on port 8000. The action may have completed; refresh the case before trying again."})


if __name__ == "__main__":
    print("RecallGuard UI: http://127.0.0.1:3000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 3000), Handler).serve_forever()
