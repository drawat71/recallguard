"""Lifecycle surface test (in-process MCP): the UI's view of the workflow.

Proves the business-action layer:
  start_case -> submit_verification -> approve_action (scoped action_id) ->
  TRACKING, with the event feed carrying every transition.
Also: insufficient-evidence stand-down, no-match stand-down, deny path,
wrong/stale action_id rejected, double approval impossible, unknown run errors.
"""
import asyncio
import json

from fastmcp import Client

from server import mcp

EXPECTED_TOOLS = sorted([
    "check_recalls",
    "get_remedy_case",
    "get_device_state",
    "get_inventory",
    "set_device_state",
    "start_remedy",
    "verify_product",
    "start_case",
    "submit_verification",
    "approve_action",
    "deny_action",
    "get_case",
    "get_events",
])


async def call(client, tool, args):
    res = await client.call_tool(tool, args)
    return json.loads(res.content[0].text)


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        assert names == EXPECTED_TOOLS, f"contract drift: {names}"
        print("TOOL CONTRACT OK:", len(names), "tools")

        # ---- happy path through the lifecycle surface ----
        s = await call(client, "start_case", {"product_key": "kitchen-air-fryer"})
        run = s["run_id"]
        assert s["state"] == "VERIFYING", s["state"]
        assert [e["to"] for e in s["events"]] == [
            "SIGNAL_DETECTED", "MATCH_REVIEW", "VERIFYING"]

        v = await call(client, "submit_verification",
                       {"run_id": run, "serial": "SN88412", "user_attested": True})
        assert v["state"] == "AWAITING_APPROVAL", v["state"]
        pending = v["pending_action"]
        assert pending["action_id"] == "disable_kitchen-air-fryer", pending
        print("pending_action:", pending["action_id"])

        # Wrong action_id is rejected — no blanket approvals.
        bad = await call(client, "approve_action",
                         {"run_id": run, "action_id": "disable_everything"})
        assert "error" in bad and "not pending approval" in bad["error"], bad

        a = await call(client, "approve_action",
                       {"run_id": run, "action_id": pending["action_id"]})
        assert a["state"] == "TRACKING", a["state"]
        seq = [e["to"] for e in a["events"]]
        assert seq == ["SIGNAL_DETECTED", "MATCH_REVIEW", "VERIFYING",
                       "MATCH_CONFIRMED", "EVIDENCE_READY", "AWAITING_APPROVAL",
                       "ACTION_EXECUTED", "REMEDY_STARTED", "TRACKING"], seq

        # The device transition is in the event feed, verified + simulated.
        action_ev = next(e for e in a["events"] if e["to"] == "ACTION_EXECUTED")
        t = action_ev["payload"]["device_transition"]
        assert (t["old_state"], t["new_state"], t["verified"]) == ("ON", "OFF", True)

        # Double approval is impossible.
        again = await call(client, "approve_action",
                           {"run_id": run, "action_id": pending["action_id"]})
        assert "error" in again, again

        # Event feed polling works.
        ev = await call(client, "get_events", {"run_id": run, "after_seq": 5})
        assert [e["seq"] for e in ev["events"]] == [6, 7, 8], ev["events"]
        assert all(set(e) == {"seq", "from", "to", "at", "payload"}
                   for e in ev["events"])
        print("HAPPY LIFECYCLE PATH PASSED")

        # ---- insufficient evidence: stand down, approval refused ----
        s2 = await call(client, "start_case", {"product_key": "kitchen-air-fryer"})
        run2 = s2["run_id"]
        v2 = await call(client, "submit_verification", {"run_id": run2})
        assert v2["state"] == "INSUFFICIENT_EVIDENCE", v2["state"]
        assert v2["terminal"] is True
        a2 = await call(client, "approve_action",
                        {"run_id": run2, "action_id": "disable_kitchen-air-fryer"})
        assert "error" in a2 and "awaiting approval" in a2["error"], a2
        print("INSUFFICIENT-EVIDENCE LIFECYCLE PATH PASSED")

        # ---- no match: immediate terminal ----
        s3 = await call(client, "start_case", {"product_key": "bedroom-vacuum"})
        assert s3["state"] == "NO_MATCH" and s3["terminal"] is True
        print("NO-MATCH LIFECYCLE PATH PASSED")

        # ---- deny path ----
        s4 = await call(client, "start_case", {"product_key": "kitchen-air-fryer"})
        run4 = s4["run_id"]
        await call(client, "submit_verification",
                   {"run_id": run4, "serial": "SN1", "user_attested": True})
        d = await call(client, "deny_action", {"run_id": run4})
        assert d["state"] == "ACTION_DECLINED" and d["terminal"] is True
        print("DENY LIFECYCLE PATH PASSED")

        # ---- unknown run ----
        u = await call(client, "get_case", {"run_id": "WF-9999"})
        assert "error" in u and "unknown run" in u["error"], u
        print("UNKNOWN-RUN HANDLING PASSED")

        print("ALL LIFECYCLE TESTS PASSED")


asyncio.run(main())
