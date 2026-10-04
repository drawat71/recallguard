"""Stateful safety workflow for RecallGuard.

This is the product: the agent knows when it does not have enough evidence
to act. Every transition is recorded as an event; the event log is the frozen
contract the UI consumes.

States:
  IDLE -> SIGNAL_DETECTED -> MATCH_REVIEW -> VERIFYING
    -> MATCH_CONFIRMED -> EVIDENCE_READY -> AWAITING_APPROVAL
      -> ACTION_EXECUTED -> REMEDY_STARTED -> TRACKING      (terminal)
    -> NO_MATCH                                             (terminal)
    -> INSUFFICIENT_EVIDENCE                                (terminal)
  AWAITING_APPROVAL -> ACTION_DECLINED                       (terminal)

INSUFFICIENT_EVIDENCE is a deliberate addition: verification can end
"likely but unverifiable", which is neither a confirmed match nor a clean
no-match. The workflow stands down with an explanation instead of acting.

Event schema (frozen):
  {"seq": int, "from": str, "to": str, "at": iso8601, "payload": {...}}
"""
from datetime import datetime, timezone

from .cases import build_remedy_draft
from .pipeline import check_product, find_recall

TERMINAL = {"NO_MATCH", "INSUFFICIENT_EVIDENCE", "ACTION_DECLINED", "TRACKING"}


class WorkflowError(Exception):
    """Illegal transition or guard violation."""


class SafetyWorkflow:
    def __init__(self, inventory, product_key, devices, case_store,
                 device_id=None, action_id=None):
        if product_key not in inventory:
            raise KeyError(f"unknown product '{product_key}'")
        self.inventory = inventory
        self.product_key = product_key
        self.item = inventory[product_key]
        self.devices = devices
        self.case_store = case_store
        self.device_id = device_id or f"{product_key}-plug"
        # Approvals are scoped to a specific action, never a blanket "yes".
        self.action_id = action_id or f"disable_{product_key}"
        self.pending_action = None
        self.state = "IDLE"
        self.events = []
        self._candidates = []
        self._match = None      # primary candidate recall match
        self._verdict = None
        self._case_id = None

    # ---- internals ----------------------------------------------------
    def _transition(self, to, payload=None):
        event = {
            "seq": len(self.events),
            "from": self.state,
            "to": to,
            "at": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }
        self.events.append(event)
        self.state = to
        return event

    def _require(self, *states):
        if self.state not in states:
            raise WorkflowError(
                f"illegal transition: state is {self.state}, "
                f"required one of {states}"
            )

    # ---- the workflow -------------------------------------------------
    def start(self):
        """Detect recall signals for the product."""
        self._require("IDLE")
        verdict, pack = check_product(self.inventory, self.product_key)
        self._verdict = verdict
        if not pack["matches"]:
            return self._transition("NO_MATCH", {
                "verdict": verdict,
                "recalls_examined": pack["recalls_examined"],
                "note": pack["note"],
            })
        self._candidates = pack["matches"]
        return self._transition("SIGNAL_DETECTED", {
            "verdict": verdict,
            "candidates": [
                {"recall_number": m["recall_number"], "title": m["title"],
                 "confidence": m["confidence"]}
                for m in pack["matches"]
            ],
        })

    def review(self):
        """Review candidate matches and pick the primary one."""
        self._require("SIGNAL_DETECTED")
        self._match = self._candidates[0]
        return self._transition("MATCH_REVIEW", {
            "primary": {
                "recall_number": self._match["recall_number"],
                "title": self._match["title"],
                "confidence": self._match["confidence"],
            },
            "evidence_needed": ["serial"],
            "evidence_hint": (
                "Model matches the recall, but CPSC data does not list serial "
                "numbers. Ask the user for the serial or a photo of the rating label."
            ),
        })

    def request_verification(self):
        """Ask the user for the missing evidence."""
        self._require("MATCH_REVIEW")
        return self._transition("VERIFYING", {
            "needed": "serial or photo of the rating label",
        })

    def submit_verification(self, serial=None, user_attested=False):
        """Process the user's evidence. Never overclaims.

        CONFIRMED: serial corroborated by CPSC data, or model match plus the
        user explicitly attesting the rating label matches (attestation is
        recorded as the evidence basis).
        """
        self._require("VERIFYING")
        verdict, pack = check_product(
            self.inventory, self.product_key, serial=serial)
        match = next(
            (m for m in pack["matches"]
             if m["recall_number"] == self._match["recall_number"]),
            None,
        )
        if verdict == "NO_MATCH" or match is None:
            return self._transition("NO_MATCH", {
                "verdict": "NO_MATCH",
                "note": "Verification ruled the product out.",
            })
        if match["confidence"] == "CONFIRMED":
            basis = "serial corroborated by CPSC recall data"
            confirmed = True
        elif user_attested:
            basis = "user attestation of the rating label"
            confirmed = True
        else:
            confirmed = False
        if not confirmed:
            return self._transition("INSUFFICIENT_EVIDENCE", {
                "verdict": "LIKELY",
                "reason": pack["note"],
                "action_taken": None,
            })
        self._match = match
        return self._transition("MATCH_CONFIRMED", {
            "recall_number": match["recall_number"],
            "basis": basis,
            "evidence": match["evidence"],
        })

    def prepare_evidence(self):
        """Build the evidence pack the approval prompt is based on."""
        self._require("MATCH_CONFIRMED")
        device = self.devices.get(self.device_id)
        return self._transition("EVIDENCE_READY", {
            "recall_number": self._match["recall_number"],
            "title": self._match["title"],
            "hazard": self._match["hazard"],
            "remedy": self._match["remedy"],
            "evidence": self._match["evidence"],
            "planned_action": {
                "device_id": self.device_id,
                "from": device["state"],
                "to": "OFF",
                "simulated": True,
            },
        })

    def request_approval(self):
        """Ask the user for explicit approval of the consequential action."""
        self._require("EVIDENCE_READY")
        self.pending_action = {
            "action_id": self.action_id,
            "description": (
                f"Turn OFF the {self.item['label']} "
                f"(simulated device {self.device_id}) and start the remedy "
                f"for CPSC recall #{self._match['recall_number']}."
            ),
        }
        return self._transition("AWAITING_APPROVAL", {
            "prompt": (
                f"The {self.item['label']} is currently "
                f"{self.devices.get(self.device_id)['state']}. "
                f"Turn it OFF and start the remedy for recall "
                f"#{self._match['recall_number']}?"
            ),
            "pending_action": self.pending_action,
        })

    def approve(self):
        """User approved: take the safe action and verify it took effect."""
        self._require("AWAITING_APPROVAL")
        transition = self.devices.set(self.device_id, "OFF")
        if not transition["verified"]:
            raise WorkflowError("device state change did not verify")
        return self._transition("ACTION_EXECUTED", {
            "device_transition": transition,
        })

    def deny(self):
        """User declined: stand down, nothing happens to the device."""
        self._require("AWAITING_APPROVAL")
        return self._transition("ACTION_DECLINED", {
            "action_taken": None,
        })

    def start_remedy(self):
        """Open the remedy case and draft the manufacturer request."""
        self._require("ACTION_EXECUTED")
        recall = find_recall(
            self.inventory, self.product_key, self._match["recall_number"])
        draft = build_remedy_draft(self.item, recall)
        case = self.case_store.create(
            self.product_key, self._match["recall_number"], draft)
        self._case_id = case["case_id"]
        return self._transition("REMEDY_STARTED", {
            "case_id": case["case_id"],
            "remedy_draft": draft,
        })

    def track(self):
        """Hand the case to tracking. Terminal for the demo flow
        (RESOLVED is a future transition, out of gate scope)."""
        self._require("REMEDY_STARTED")
        self.case_store.set_state(self._case_id, "TRACKING")
        return self._transition("TRACKING", {
            "case_id": self._case_id,
            "note": "Case tracked until resolved.",
        })
