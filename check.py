"""RecallGuard Phase 1a gate: one command -> CPSC -> compare -> verdict + evidence.

Usage:
    python check.py                          # kitchen air fryer, no serial
    python check.py --serial ABC123          # with a serial number
    python check.py --product bedroom-vacuum # a product with no recalls
"""
import argparse
import json
import sys

from recallguard.cpsc import search_recalls
from recallguard.matcher import match_product


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="kitchen-air-fryer")
    ap.add_argument("--serial", default=None)
    ap.add_argument("--inventory", default="inventory.json")
    args = ap.parse_args()

    with open(args.inventory) as f:
        inventory = json.load(f)
    if args.product not in inventory:
        sys.exit(f"unknown product '{args.product}' (see inventory.json)")
    item = inventory[args.product]

    recalls = search_recalls(item["search_keyword"])
    verdict, pack = match_product(item, recalls, serial=args.serial)
    print(json.dumps(pack, indent=2))


if __name__ == "__main__":
    main()
