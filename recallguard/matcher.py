"""Match a household product against CPSC recalls -> verdict + evidence pack.

Verdicts:
  CONFIRMED - model matches the recall AND the serial is corroborated by recall data
  LIKELY    - model matches the recall, but serial-level evidence is missing
  NO_MATCH  - nothing in the recall data matches this product

The point: the agent reports what the evidence supports, nothing more.
"""
import re
from datetime import datetime, timezone

MODEL_RE = re.compile(r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]+)+\b")


def _norm(s):
    return (s or "").strip().lower()


def extract_models(text):
    """Model numbers live in the recall Description text (e.g. NS-AF5DSS2)."""
    return sorted(set(MODEL_RE.findall(text or "")))


def _recall_text(recall):
    parts = [recall.get("Title") or "", recall.get("Description") or ""]
    for p in recall.get("Products") or []:
        parts.append(p.get("Model") or "")
        parts.append(p.get("Name") or "")
        parts.append(p.get("Description") or "")
    return " ".join(parts)


def match_product(item, recalls, serial=None):
    """Return (verdict, evidence_pack)."""
    model = _norm(item.get("model"))
    serial = _norm(serial or item.get("serial"))
    examined = []
    candidates = []

    for r in recalls:
        text = _recall_text(r)
        text_l = text.lower()
        models = extract_models(text)
        model_hit = model and (
            model in [m.lower() for m in models] or model in text_l
        )
        serial_hit = serial and serial in text_l
        examined.append(r.get("RecallNumber"))

        if not model_hit:
            continue

        hazards = [h.get("Name") for h in (r.get("Hazards") or []) if h.get("Name")]
        candidates.append(
            {
                "recall_number": r.get("RecallNumber"),
                "title": r.get("Title"),
                "recall_date": r.get("RecallDate"),
                "hazard": hazards[0] if hazards else None,
                "remedy": r.get("Remedy"),
                "consumer_contact": r.get("ConsumerContact"),
                "model_match": item.get("model"),
                "serial_match": serial if serial_hit else None,
                "confidence": "CONFIRMED" if serial_hit else "LIKELY",
                "evidence": (
                    f"Model {item.get('model')} appears in CPSC recall "
                    f"#{r.get('RecallNumber')}; serial corroborated by recall data."
                    if serial_hit
                    else f"Model {item.get('model')} appears in CPSC recall "
                    f"#{r.get('RecallNumber')}, but the recall data does not list "
                    f"serial numbers — serial verification is needed before acting."
                ),
            }
        )

    if not candidates:
        verdict = "NO_MATCH"
        note = (
            f"Checked {len(recalls)} CPSC recall(s) for "
            f"'{item.get('search_keyword')}'; model {item.get('model')} appears in none of them."
        )
    elif any(c["confidence"] == "CONFIRMED" for c in candidates):
        verdict = "CONFIRMED"
        note = "Model and serial both corroborated by CPSC recall data."
    else:
        verdict = "LIKELY"
        note = (
            "Model matches a CPSC recall, but serial-level evidence is missing. "
            "Ask the user for the serial/photo before any consequential action."
        )

    pack = {
        "verdict": verdict,
        "product": {
            "label": item.get("label"),
            "brand": item.get("brand"),
            "model": item.get("model"),
            "serial_provided": bool(serial),
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "recalls_examined": len(recalls),
        "matches": candidates,
        "note": note,
    }
    return verdict, pack
