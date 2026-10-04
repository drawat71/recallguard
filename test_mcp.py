"""End-to-end frozen lifecycle contract test over real MCP Streamable HTTP.

Run with server.py available at http://127.0.0.1:8000/mcp/ and live CPSC access.
The happy path deliberately runs first so a fresh backend verifies ON -> OFF.
"""
import asyncio
import json

from fastmcp import Client

MCP_URL = "http://127.0.0.1:8000/mcp/"
EXPECTED_TOOLS = sorted([
    "approve_action",
    "check_recalls",
    "deny_action",
    "get_case",
    "get_device_state",
    "get_events",
    "get_inventory",
    "get_remedy_case",
    "set_device_state",
    "start_case",
    "start_remedy",
    "submit_verification",
    "verify_product",
])
EVENT_KEYS = {"seq", "from", "to", "at", "payload"}
HAPPY_STATES = [
    "SIGNAL_DETECTED",
    "MATCH_REVIEW",
    "VERIFYING",
    "MATCH_CONFIRMED",
    "EVIDENCE_READY",
    "AWAITING_APPROVAL",
    "ACTION_EXECUTED",
    "REMEDY_STARTED",
    "TRACKING",
]


async def call(client, tool, args):
    result = await client.call_tool(tool, args)
    assert not result.is_error, f"{tool} failed: {result.content}"
    return json.loads(result.content[0].text)


async def main():
    async with Client(MCP_URL) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools)
        assert names == EXPECTED_TOOLS, f"frozen MCP contract changed: {names}"
        print("13-tool MCP contract: PASS")

        inventory = await call(client, "get_inventory", {})
        assert {item["key"] for item in inventory} >= {
            "kitchen-air-fryer", "bedroom-vacuum"
        }
        print("HTTP inventory: PASS")

        # Run first against the server's seeded ON device to confirm the full transport path.
        device_before = await call(client, "get_device_state", {
            "device_id": "kitchen-air-fryer-plug"
        })
        assert device_before["state"] == "ON", (
            "restart server.py before test_mcp.py to reset the simulated device"
        )
        started = await call(client, "start_case", {
            "product_key": "kitchen-air-fryer"
        })
        run_id = started["run_id"]
        assert started["state"] == "VERIFYING"
        assert [event["to"] for event in started["events"]] == [
            "SIGNAL_DETECTED", "MATCH_REVIEW", "VERIFYING"
        ]

        verified = await call(client, "submit_verification", {
            "run_id": run_id,
            "serial": "DEMO-SN88412",
            "user_attested": True,
        })
        assert verified["state"] == "AWAITING_APPROVAL"
        pending = verified["pending_action"]
        assert pending["action_id"] == "disable_kitchen-air-fryer"

        wrong = await call(client, "approve_action", {
            "run_id": run_id, "action_id": "wrong-action"
        })
        assert "error" in wrong
        happy = await call(client, "approve_action", {
            "run_id": run_id, "action_id": pending["action_id"]
        })
        assert happy["state"] == "TRACKING" and happy["terminal"]
        assert [event["to"] for event in happy["events"]] == HAPPY_STATES
        transition = happy["events"][6]["payload"]["device_transition"]
        assert (transition["old_state"], transition["new_state"],
                transition["verified"], transition["simulated"]) == (
                    "ON", "OFF", True, True
                )
        print("HTTP happy path, scoped approval, ON -> OFF verified: PASS")

        case = await call(client, "get_case", {"run_id": run_id})
        assert case["state"] == "TRACKING" and case["terminal"]
        full_feed = await call(client, "get_events", {
            "run_id": run_id, "after_seq": -1
        })
        assert [event["seq"] for event in full_feed["events"]] == list(range(9))
        assert all(set(event) == EVENT_KEYS for event in full_feed["events"])
        tail = await call(client, "get_events", {
            "run_id": run_id, "after_seq": 5
        })
        assert [event["seq"] for event in tail["events"]] == [6, 7, 8]
        assert not (await call(client, "get_events", {
            "run_id": run_id, "after_seq": 8
        }))["events"]
        again = await call(client, "approve_action", {
            "run_id": run_id, "action_id": pending["action_id"]
        })
        assert "error" in again
        print("HTTP get_case, full/incremental event feed, double-approval guard: PASS")

        # An inconclusive user verification must not alter the shared device.
        device_before = await call(client, "get_device_state", {
            "device_id": "kitchen-air-fryer-plug"
        })
        inconclusive_start = await call(client, "start_case", {
            "product_key": "kitchen-air-fryer"
        })
        inconclusive = await call(client, "submit_verification", {
            "run_id": inconclusive_start["run_id"]
        })
        assert inconclusive["state"] == "INSUFFICIENT_EVIDENCE"
        assert inconclusive["terminal"]
        blocked = await call(client, "approve_action", {
            "run_id": inconclusive_start["run_id"],
            "action_id": "disable_kitchen-air-fryer",
        })
        assert "error" in blocked
        device_after = await call(client, "get_device_state", {
            "device_id": "kitchen-air-fryer-plug"
        })
        assert device_after["state"] == device_before["state"]
        print("HTTP insufficient-evidence stand-down and unchanged device: PASS")

        no_match = await call(client, "start_case", {
            "product_key": "bedroom-vacuum"
        })
        assert no_match["state"] == "NO_MATCH" and no_match["terminal"]
        first_event = (await call(client, "get_events", {
            "run_id": no_match["run_id"], "after_seq": -1
        }))["events"]
        assert len(first_event) == 1 and first_event[0]["seq"] == 0
        print("HTTP no-match and sequence-zero event: PASS")

        deny_start = await call(client, "start_case", {
            "product_key": "kitchen-air-fryer"
        })
        deny_ready = await call(client, "submit_verification", {
            "run_id": deny_start["run_id"],
            "serial": "DEMO-DENY",
            "user_attested": True,
        })
        assert deny_ready["state"] == "AWAITING_APPROVAL"
        declined = await call(client, "deny_action", {
            "run_id": deny_start["run_id"]
        })
        assert declined["state"] == "ACTION_DECLINED" and declined["terminal"]
        assert all(event["to"] != "ACTION_EXECUTED" for event in declined["events"])
        print("HTTP deny stand-down: PASS")

        unknown = await call(client, "get_case", {"run_id": "WF-9999"})
        assert "error" in unknown
        remedy = await call(client, "get_remedy_case", {
            "case_id": happy["events"][7]["payload"]["case_id"]
        })
        assert remedy["state"] == "TRACKING"
        print("HTTP unknown-run handling and renamed remedy lookup: PASS")
        print("ALL MCP STREAMABLE HTTP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
