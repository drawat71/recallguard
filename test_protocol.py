"""In-process MCP protocol test — no network config changes.

Proves over the real MCP dispatch layer (in-memory transport):
  client -> list tools -> call check_recalls -> real CPSC result ->
  call verify_product -> expected verdict + evidence.
"""
import asyncio
import json

from fastmcp import Client

from server import mcp

EXPECTED_TOOLS = [
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
]


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        print("TOOLS:", names)
        assert names == EXPECTED_TOOLS, f"tool contract drift: {names}"

        # check_recalls, no serial -> LIKELY on the real Insignia recall
        r1 = await client.call_tool(
            "check_recalls", {"product_key": "kitchen-air-fryer"}
        )
        pack = json.loads(r1.content[0].text)
        matched = [m["recall_number"] for m in pack["matches"]]
        print("check_recalls VERDICT:", pack["verdict"], "| recalls:", matched)
        assert pack["verdict"] == "LIKELY"
        assert "24159" in matched, "expected the real Insignia recall #24159"
        assert pack["matches"][0]["evidence"]

        # verify_product with a serial -> well-formed evidence, honest verdict
        r2 = await client.call_tool(
            "verify_product",
            {"product_key": "kitchen-air-fryer", "serial": "SN88412"},
        )
        v = json.loads(r2.content[0].text)
        print(
            "verify_product VERDICT:", v["verdict"],
            "| serial_provided:", v["product"]["serial_provided"],
        )
        assert v["product"]["serial_provided"] is True
        assert v["verdict"] in ("LIKELY", "CONFIRMED")
        assert v["note"] and v["matches"]

        # NO_MATCH path still clean
        r3 = await client.call_tool(
            "check_recalls", {"product_key": "bedroom-vacuum"}
        )
        p3 = json.loads(r3.content[0].text)
        print("vacuum VERDICT:", p3["verdict"])
        assert p3["verdict"] == "NO_MATCH"

        print("IN-PROCESS MCP PROTOCOL TEST PASSED")


asyncio.run(main())
