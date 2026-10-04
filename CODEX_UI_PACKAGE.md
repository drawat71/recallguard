# Codex work package: RecallGuard web UI

## Objective

Build a web interface that consumes the frozen workflow events and renders
**chat + recall evidence + state stepper + approval controls**.
The UI visualizes real workflow states and approvals. It invents nothing.

## Context

RecallGuard is a household safety workflow agent. The backend is done and
frozen: an MCP server (`server.py`, Streamable HTTP on `127.0.0.1:8000`)
wrapping a stateful safety workflow (`recallguard/workflow.py`) over live
CPSC recall data. The product thesis: the agent knows when it does not have
enough evidence to act.

## Contract (FROZEN — do not change)

**The UI may call ONLY these 6 lifecycle tools** (MCP, Streamable HTTP):

| Tool | Purpose |
|---|---|
| `start_case(product_key)` | Start a safety workflow. Returns `run_id`, `state`, `pending_action`, `events`. |
| `submit_verification(run_id, serial?, user_attested?)` | Submit label evidence. |
| `approve_action(run_id, action_id)` | Approve the pending action — `action_id` must equal `pending_action.action_id`. |
| `deny_action(run_id)` | Decline the pending action. |
| `get_case(run_id)` | Run status: `state`, `terminal`, `pending_action`, `event_count`. |
| `get_events(run_id, after_seq?)` | Event feed for polling. |

Layering (enforced by the backend): UI → business actions → workflow engine →
state transitions → event feed. **There is no tool that sets state directly,
so do not try to drive transitions from the UI.**

**Event schema (frozen):** `{"seq", "from", "to", "at", "payload"}`

**States:** `IDLE → SIGNAL_DETECTED → MATCH_REVIEW → VERIFYING →`
`MATCH_CONFIRMED` / `NO_MATCH` / `INSUFFICIENT_EVIDENCE` (all three terminal-capable)
`→ EVIDENCE_READY → AWAITING_APPROVAL → ACTION_EXECUTED` / `ACTION_DECLINED`
`→ REMEDY_STARTED → TRACKING` (terminal).

**Approval is per-action, never a blanket yes.** `approve_action` takes the
`pending_action.action_id` returned by the API (e.g. `disable_kitchen-air-fryer`).
Render the `pending_action.description` on the approval control and send back
that exact id. A wrong or stale id is rejected by the backend.

**Key product behaviors the UI must show honestly:**
- `INSUFFICIENT_EVIDENCE` is a terminal stand-down: likely match, verification
  inconclusive, no consequential action. Render as a stand-down screen —
  never show approval controls here.
- `NO_MATCH` is a clean stand-down, not an error.
- The device action is **simulated**; every device payload carries
  `"simulated": true`. Label it as simulated in the UI.

## Demo script the UI must support

1. Chat: "check my air fryer" → `start_case("kitchen-air-fryer")` →
   stepper shows `SIGNAL_DETECTED → MATCH_REVIEW → VERIFYING`;
   chat asks for the serial / label photo.
2. User provides serial + confirms the label (`user_attested: true`) →
   `submit_verification` → stepper advances to `AWAITING_APPROVAL`;
   evidence panel shows recall #24159, hazard, remedy, and the evidence basis.
3. Approval card shows the pending action description with
   Approve / Deny → `approve_action(run_id, <exact pending action_id>)` →
   stepper runs `ACTION_EXECUTED → REMEDY_STARTED → TRACKING`;
   device panel shows the verified `ON → OFF` transition (labeled simulated);
   remedy panel shows the draft and case id.

Seeded inventory (`inventory.json`): `kitchen-air-fryer`
(Insignia NS-AF5DSS2 → live CPSC recall #24159, LIKELY),
`bedroom-vacuum` (Dyson SV22 → NO_MATCH, good for the stand-down path).

## Non-goals

- Do not alter backend contracts or business logic: no changes to
  `recallguard/`, `server.py` tools, the state machine, or the event schema.
- No new MCP tools. No accounts/auth. No mobile app.
- Do not mock the workflow: every state in the stepper must come from
  `get_events`, every approval from `approve_action`.

## Files you may touch

- New directory `ui/` only. Everything else is read-only.

## Acceptance criteria

1. `ui/` runs locally and talks to the MCP server over Streamable HTTP
   (`server.py` running on `127.0.0.1:8000`).
2. Chat panel drives the full demo script above against the real backend.
3. State stepper renders every event from `get_events` in order, with
   payloads visible (evidence basis, device transition, case id).
4. `INSUFFICIENT_EVIDENCE` and `NO_MATCH` render as stand-down screens
   with no approval controls.
5. Approve sends the exact `pending_action.action_id` from the API —
   never a hardcoded or generic yes.
6. Backend test suites still pass untouched:
   `.venv/bin/python test_protocol.py test_lifecycle.py test_workflow.py`.

## Run the backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py   # Streamable HTTP on 127.0.0.1:8000
```
