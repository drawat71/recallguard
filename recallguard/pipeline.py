"""Recall check pipeline: inventory item -> live CPSC -> verdict + evidence pack.

Single implementation shared by the CLI, the MCP server, and the workflow.
"""
from .cpsc import search_recalls
from .matcher import match_product


def check_product(inventory, product_key, serial=None):
    """Return (verdict, evidence_pack) for one household product."""
    if product_key not in inventory:
        raise KeyError(f"unknown product '{product_key}'")
    item = inventory[product_key]
    recalls = search_recalls(item["search_keyword"])
    return match_product(item, recalls, serial=serial)


def find_recall(inventory, product_key, recall_number):
    """Return the raw CPSC recall dict for a recall number, or None."""
    item = inventory[product_key]
    recalls = search_recalls(item["search_keyword"])
    return next(
        (r for r in recalls if str(r.get("RecallNumber")) == str(recall_number)),
        None,
    )
