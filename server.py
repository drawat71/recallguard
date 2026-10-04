"""RecallGuard MCP server — Phase 1b (contract frozen).

Track tech (actually imported/called, per Alexa+ track rules):
  - FastMCP server, MCP spec 2025-11-25+, Streamable HTTP transport.

Run:  .venv/bin/python server.py        (Streamable HTTP on :8000)
Tools: get_inventory, check_recalls, verify_product, get_device_state,
       set_device_state, start_remedy, get_case
"""
import os

# Set before fastmcp is imported: skip the startup "check for updates" phone-home
# (it also trips over proxy env vars in sandboxed environments).
# Override with FASTMCP_CHECK_FOR_UPDATES=on if you ever want it.
os.environ.setdefault("FASTMCP_CHECK_FOR_UPDATES", "off")

import json
from pathlib import Path

from fastmcp import FastMCP

from recallguard.cases import CaseStore, build_remedy_draft
from recallguard.devices import SimulatedDeviceRegistry
from recallguard.pipeline import check_product, find_recall
from recallguard.workflow import SafetyWorkflow, WorkflowError, TERMINAL

BASE = Path(__file__).resolve().parent
mcp = FastMCP("RecallGuard")

# Shared with the workflow module (same slice, same owner).
devices = SimulatedDeviceRegistry({"kitchen-air-fryer-plug": "ON"})
case_store = CaseStore(BASE / "cases.json")

# In-flight workflow runs. In-memory: a server restart drops them, which is
# fine for the demo; remedy cases persist in the CaseStore.
_workflows = {}


def _load_inventory():
    return json.loads((BASE / "inventory.json").read_text())


@mcp.tool()
def get_inventory() -> str:
    """List the household inventory products."""
    inv = _load_inventory()
    return json.dumps([{"key": k, **v} for k, v in inv.items()], indent=2)


@mcp.tool()
def check_recalls(product_key: str, serial: str | None = None) -> str:
    """Check one household product against live CPSC recalls.

    Returns a verdict (CONFIRMED / LIKELY / NO_MATCH) plus an evidence pack.
    LIKELY means the model matches but serial-level evidence is missing —
    ask the user for the serial/photo before any consequential action.
    """
    try:
        _verdict, pack = check_product(_load_inventory(), product_key, serial=serial)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(pack, indent=2)


@mcp.tool()
def verify_product(product_key: str, serial: str) -> str:
    """Verify a product's identity against a candidate recall using its serial number.

    Call this after check_recalls returns LIKELY. Returns CONFIRMED only if the
    serial is corroborated by CPSC recall data; otherwise LIKELY with a note
    explaining what evidence is still missing. Never overclaims.
    """
    try:
        _verdict, pack = check_product(_load_inventory(), product_key, serial=serial)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(pack, indent=2)


@mcp.tool()
def get_device_state(device_id: str) -> str:
    """Read the state of a simulated smart-home device."""
    return json.dumps(devices.get(device_id))


@mcp.tool()
def set_device_state(device_id: str, state: str) -> str:
    """Set the state of a simulated smart-home device (ON/OFF).

    Only call after explicit user approval. Returns the verified state transition.
    """
    return json.dumps(devices.set(device_id, state))


@mcp.tool()
def start_remedy(product_key: str, recall_number: str) -> str:
    """Open a remedy case for a confirmed/likely recall match and draft the
    manufacturer's replacement/repair request from the recall data.

    Only call after explicit user approval. Nothing is submitted externally —
    the draft is for the user to send.
    """
    inv = _load_inventory()
    if product_key not in inv:
        return json.dumps({"error": f"unknown product '{product_key}'"})
    recall = find_recall(inv, product_key, recall_number)
    if recall is None:
        return json.dumps({"error": f"recall #{recall_number} not found in live data"})
    draft = build_remedy_draft(inv[product_key], recall)
    return json.dumps(case_store.create(product_key, recall_number, draft), indent=2)


@mcp.tool()
def get_remedy_case(case_id: str) -> str:
    """Get the current state of a remedy case (e.g. RG-24159-001)."""
    case = case_store.get(case_id)
    if case is None:
        return json.dumps({"error": f"unknown case '{case_id}'"})
    return json.dumps(case, indent=2)


# ---------------------------------------------------------------------------
# Workflow lifecycle surface (frozen). The UI calls these business actions;
# the workflow engine decides every state transition. The UI must never
# drive state transitions directly.
# ---------------------------------------------------------------------------

def _lookup_run(run_id):
    wf = _workflows.get(run_id)
    if wf is None:
        raise KeyError(f"unknown run '{run_id}'")


def _run_snapshot(run_id, wf):
    return json.dumps({
        "run_id": run_id,
        "state": wf.state,
        "terminal": wf.state in TERMINAL,
        "pending_action": wf.pending_action,
        "events": wf.events,
    }, indent=2)


@mcp.tool()
def start_case(product_key: str) -> str:
    """Start a safety workflow for a household product.

    Runs the workflow forward to the next point needing user input and
    returns the run id, current state, and full event log. A product with
    no recall signal returns the terminal NO_MATCH state immediately.
    """
    inv = _load_inventory()
    if product_key not in inv:
        return json.dumps({"error": f"unknown product '{product_key}'"})
    run_id = f"WF-{len(_workflows) + 1:04d}"
    wf = SafetyWorkflow(inv, product_key, devices, case_store,
                        device_id=f"{product_key}-plug")
    _workflows[run_id] = wf
    try:
        wf.start()
        if wf.state == "SIGNAL_DETECTED":
            wf.review()
        if wf.state == "MATCH_REVIEW":
            wf.request_verification()
    except WorkflowError as e:
        return json.dumps({"error": str(e), "run_id": run_id})
    return _run_snapshot(run_id, wf)


@mcp.tool()
def submit_verification(run_id: str, serial: str | None = None,
                        user_attested: bool = False) -> str:
    """Submit evidence for the pending verification step.

    serial: the serial from the product's rating label (if the user provided it).
    user_attested: True if the user explicitly confirmed the label matches the
    recalled model. Recorded as the evidence basis; never assumed.
    Advances to AWAITING_APPROVAL on confirmation, or to a terminal
    INSUFFICIENT_EVIDENCE / NO_MATCH state otherwise.
    """
    try:
        _lookup_run(run_id)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    wf = _workflows[run_id]
    try:
        wf.submit_verification(serial=serial, user_attested=user_attested)
        if wf.state == "MATCH_CONFIRMED":
            wf.prepare_evidence()
        if wf.state == "EVIDENCE_READY":
            wf.request_approval()
    except WorkflowError as e:
        return json.dumps(
            {"error": str(e), "run_id": run_id, "state": wf.state})
    return _run_snapshot(run_id, wf)


@mcp.tool()
def approve_action(run_id: str, action_id: str) -> str:
    """Approve the pending consequential action — and only that action.

    action_id must equal the pending_action.action_id from get_case; a wrong
    or stale action_id is rejected. One approval never covers anything else.
    On approval the workflow executes the action (verified), starts the
    remedy, and moves to TRACKING.
    """
    try:
        _lookup_run(run_id)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    wf = _workflows[run_id]
    try:
        if wf.state != "AWAITING_APPROVAL":
            raise WorkflowError(
                f"nothing is awaiting approval (state is {wf.state})")
        pending = wf.pending_action or {}
        if action_id != pending.get("action_id"):
            raise WorkflowError(
                f"action '{action_id}' is not pending approval")
        wf.approve()
        wf.start_remedy()
        wf.track()
    except WorkflowError as e:
        return json.dumps(
            {"error": str(e), "run_id": run_id, "state": wf.state})
    return _run_snapshot(run_id, wf)


@mcp.tool()
def deny_action(run_id: str) -> str:
    """Decline the pending action. The workflow stands down; the device is untouched."""
    try:
        _lookup_run(run_id)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    wf = _workflows[run_id]
    try:
        wf.deny()
    except WorkflowError as e:
        return json.dumps(
            {"error": str(e), "run_id": run_id, "state": wf.state})
    return _run_snapshot(run_id, wf)


@mcp.tool()
def get_case(run_id: str) -> str:
    """Get the current status of a workflow run."""
    try:
        _lookup_run(run_id)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    wf = _workflows[run_id]
    return json.dumps({
        "run_id": run_id,
        "state": wf.state,
        "terminal": wf.state in TERMINAL,
        "product_key": wf.product_key,
        "pending_action": wf.pending_action,
        "event_count": len(wf.events),
    }, indent=2)


@mcp.tool()
def get_events(run_id: str, after_seq: int = 0) -> str:
    """Get the workflow's event feed (the frozen contract the UI renders).

    after_seq supports polling: only events with seq > after_seq are returned.
    Event schema: {"seq", "from", "to", "at", "payload"}.
    """
    try:
        _lookup_run(run_id)
    except KeyError as e:
        return json.dumps({"error": str(e)})
    wf = _workflows[run_id]
    return json.dumps({
        "run_id": run_id,
        "state": wf.state,
        "events": [e for e in wf.events if e["seq"] > after_seq],
    }, indent=2)


if __name__ == "__main__":
    # Streamable HTTP — the transport the Alexa+ track requires.
    mcp.run(transport="http", host="127.0.0.1", port=8000)
