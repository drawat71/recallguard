# Validation — 2026-09-27

Environment: macOS, Python 3.11.2, FastMCP 4.0.10 from the pinned requirement, Node 26.0.0. Python used the Mac system certificate bundle at `/etc/ssl/cert.pem`; TLS verification remained enabled.

## Full ordered gate

`.venv/bin/python ui/tests/run_all.py` completed with exit code 0:

- Updated `test_mcp.py`: 13-tool frozen contract over actual Streamable HTTP; seeded ON → OFF → verified; exact and stale approval; all four workflow outcomes; current remedy lookup; full and incremental event feed; sequence zero; guards and unknown runs.
- `ui/tests/live_http.py`: all four paths through the UI adapter, real MCP HTTP server, and live CPSC data; restoration, schema, incremental polling, and adapter allowlist.
- Original `test_protocol.py`, `test_lifecycle.py`, `test_workflow.py`, and `check.py` all passed.
- 8 Python UI-adapter and optional Bedrock tests and 14 JavaScript UI/state tests passed.

The CPSC lookup returned live recall #24159 for the seeded Insignia air fryer and NO_MATCH for the seeded Dyson vacuum. The HTTP gate began after a backend restart, so it confirmed an ON → OFF transition. Tests create local in-memory workflow runs and remedy drafts, leave the simulated device OFF, and send nothing to a manufacturer.

## Browser verification

- Happy path reached TRACKING with nine backend events, a verified simulated ON → OFF event, and a remedy draft. Reload restored the same case.
- Insufficient evidence, no-match, and deny each showed their backend terminal state and had no approval button.
- A backend restart expired the saved run and produced a clear recovery message. A fresh verification case was then started.
- The optional Bedrock explainer was clicked with AWS unconfigured; the UI showed setup guidance, made no AWS request, and kept the case at VERIFYING.
- Desktop and 390px mobile layouts were inspected; mobile page had no horizontal overflow.

## Scope

`test_mcp.py` now exercises the current 13-tool Streamable HTTP contract; its obsolete assertions are gone. The optional AWS layer is isolated in `ui/aws/` and a local sidecar route. It makes one bounded Bedrock explanation request only when configured and explicitly clicked; workflow decisions, MCP contracts, and event schema are unchanged. Bedrock unit tests use a mocked client. No AWS credentials or model were configured, so no live Bedrock inference was made. No demo video or deployment is part of this gate.
