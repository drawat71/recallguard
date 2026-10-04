"""Live CPSC recall lookup (keyless JSON API)."""
import json
import urllib.parse
import urllib.request

BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
TIMEOUT = 25


def search_recalls(product_keyword):
    """Return list of recall dicts for a product keyword. Empty list on no match."""
    params = urllib.parse.urlencode({"format": "json", "ProductName": product_keyword})
    req = urllib.request.Request(
        f"{BASE}?{params}", headers={"User-Agent": "RecallGuard-hackathon/0.1"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.load(resp)
    return data if isinstance(data, list) else []
