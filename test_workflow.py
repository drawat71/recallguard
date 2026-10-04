"""Gate test: prove the three workflow paths and the guard rails.

  happy path:        likely match -> verification -> approval ->
                     simulated OFF -> remedy started -> tracking
  insufficient evidence path: likely match -> verification inconclusive ->
                     no consequential action (and approval is refused)
  no-match path:     stand down cleanly

  guards: consequential actions are impossible without approval;
          illegal transitions raise.
"""
import json
import tempfile
from pathlib import Path

from recallguard.cases import CaseStore
from recallguard.devices import SimulatedDeviceRegistry
from recallguard.workflow import SafetyWorkflow, WorkflowError, TERMINAL

BASE = Path(__file__).resolve().parent
INVENTORY = json.loads((BASE / "inventory.json").read_text())


def make_wf(product_key="kitchen-air-fryer"):
    tmp = tempfile.mkdtemp()
    return SafetyWorkflow(
        INVENTORY,
        product_key,
        SimulatedDeviceRegistry({"kitchen-air-fryer-plug": "ON"}),
        CaseStore(Path(tmp) / "cases.json"),
        device_id="kitchen-air-fryer-plug",
    )


def states(wf):
    return [e["to"] for e in wf.events]


def test_happy_path():
    wf = make_wf()
    wf.start()
    wf.review()
    wf.request_verification()
    # Serial supplied + user attests the rating label matches.
    wf.submit_verification(serial="SN88412", user_attested=True)
    wf.prepare_evidence()
    wf.request_approval()
    wf.approve()
    wf.start_remedy()
    wf.track()

    assert states(wf) == [
        "SIGNAL_DETECTED", "MATCH_REVIEW", "VERIFYING", "MATCH_CONFIRMED",
        "EVIDENCE_READY", "AWAITING_APPROVAL", "ACTION_EXECUTED",
        "REMEDY_STARTED", "TRACKING",
    ], states(wf)
    assert wf.state in TERMINAL

    # The device transition really happened and was verified.
    action = next(e for e in wf.events if e["to"] == "ACTION_EXECUTED")
    t = action["payload"]["device_transition"]
    assert (t["old_state"], t["new_state"], t["verified"], t["simulated"]) == (
        "ON", "OFF", True, True)
    assert wf.devices.get("kitchen-air-fryer-plug")["state"] == "OFF"

    # A remedy case exists with a draft.
    remedy = next(e for e in wf.events if e["to"] == "REMEDY_STARTED")
    assert remedy["payload"]["case_id"].startswith("RG-24159")
    assert "Recall remedy request" in remedy["payload"]["remedy_draft"]
    assert wf.case_store.get(remedy["payload"]["case_id"])["state"] == "TRACKING"

    # Approval actually gated the action: the prompt named the device + recall.
    appr = next(e for e in wf.events if e["to"] == "AWAITING_APPROVAL")
    assert "OFF" in appr["payload"]["prompt"] and "24159" in appr["payload"]["prompt"]
    print("HAPPY PATH PASSED")


def test_insufficient_evidence_path():
    wf = make_wf()
    wf.start()
    wf.review()
    wf.request_verification()
    # No serial, no attestation: the agent must not act.
    wf.submit_verification()

    assert wf.state == "INSUFFICIENT_EVIDENCE", wf.state
    assert wf.state in TERMINAL
    assert states(wf) == [
        "SIGNAL_DETECTED", "MATCH_REVIEW", "VERIFYING", "INSUFFICIENT_EVIDENCE"]

    # No consequential action happened or can happen.
    assert wf.devices.get("kitchen-air-fryer-plug")["state"] == "ON"
    try:
        wf.approve()
    except WorkflowError:
        pass
    else:
        raise AssertionError("approve() must be impossible without approval state")
    try:
        wf.start_remedy()
    except WorkflowError:
        pass
    else:
        raise AssertionError("start_remedy() must be impossible here")
    print("INSUFFICIENT-EVIDENCE PATH PASSED")


def test_no_match_path():
    wf = make_wf("bedroom-vacuum")
    wf.start()

    assert wf.state == "NO_MATCH", wf.state
    assert wf.state in TERMINAL
    assert states(wf) == ["NO_MATCH"]
    evt = wf.events[0]
    assert evt["payload"]["verdict"] == "NO_MATCH"
    assert evt["payload"]["recalls_examined"] > 0
    print("NO-MATCH PATH PASSED")


def test_guards():
    wf = make_wf()
    # Can't skip ahead: approval before verification is impossible.
    for fn in (wf.review, wf.request_verification, wf.prepare_evidence,
               wf.request_approval, wf.approve, wf.start_remedy, wf.track):
        try:
            fn()
        except WorkflowError:
            pass
        else:
            raise AssertionError("illegal transition did not raise")
    # Deny path stands down cleanly.
    wf2 = make_wf()
    wf2.start(); wf2.review(); wf2.request_verification()
    wf2.submit_verification(serial="SN88412", user_attested=True)
    wf2.prepare_evidence(); wf2.request_approval(); wf2.deny()
    assert wf2.state == "ACTION_DECLINED"
    assert wf2.devices.get("kitchen-air-fryer-plug")["state"] == "ON"
    print("GUARDS PASSED")


if __name__ == "__main__":
    test_happy_path()
    test_insufficient_evidence_path()
    test_no_match_path()
    test_guards()
    print("ALL WORKFLOW GATE TESTS PASSED")
