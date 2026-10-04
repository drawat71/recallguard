"""Persistent remedy case store (JSON file) + remedy draft builder."""
import json
from datetime import datetime, timezone
from pathlib import Path


def build_remedy_draft(item, recall):
    """Draft the manufacturer's replacement/repair request from recall data.

    The user sends it; nothing is ever submitted externally by the agent.
    """
    hazards = [h.get("Name") for h in (recall.get("Hazards") or []) if h.get("Name")]
    return (
        f"Subject: Recall remedy request — {item.get('brand')} {item.get('label')} "
        f"(model {item.get('model')})\n\n"
        f"Hello, I am writing regarding CPSC recall #{recall.get('RecallNumber')}: "
        f"{recall.get('Title')}\n"
        f"Hazard: {hazards[0] if hazards else 'see recall notice'}\n"
        f"My unit: brand {item.get('brand')}, model {item.get('model')}.\n"
        f"Please advise on the stated remedy: {recall.get('Remedy') or 'see recall notice'}.\n"
        f"Contact from recall notice: {recall.get('ConsumerContact') or 'see recall notice'}\n"
    )


class CaseStore:
    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def _write(self, cases):
        self.path.write_text(json.dumps(cases, indent=2))

    def create(self, product_key, recall_number, remedy_draft):
        cases = self._read()
        case_id = f"RG-{recall_number}-{len(cases) + 1:03d}"
        cases[case_id] = {
            "case_id": case_id,
            "product_key": product_key,
            "recall_number": str(recall_number),
            "state": "REMEDY_STARTED",
            "remedy_draft": remedy_draft,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write(cases)
        return cases[case_id]

    def get(self, case_id):
        return self._read().get(case_id)

    def set_state(self, case_id, state):
        cases = self._read()
        if case_id not in cases:
            return None
        cases[case_id]["state"] = state
        self._write(cases)
        return cases[case_id]
