# RecallGuard — Build Plan

**Status (2026-09-27): workflow gate PASSED.** `SafetyWorkflow` proves all three paths against live CPSC data:
happy path (LIKELY → attested verification → approval → simulated OFF verified → remedy → TRACKING),
insufficient-evidence path (stands down, device untouched, `approve()` refused),
no-match path (clean stand-down). Illegal transitions raise; deny path stands down.
Event schema frozen: `{"seq", "from", "to", "at", "payload"}` — this is what the UI will consume.
One deliberate addition beyond the spec: terminal state `INSUFFICIENT_EVIDENCE`
("likely but unverifiable" is neither confirmed nor a clean no-match — the workflow
refuses to act). Deny → `ACTION_DECLINED` also handled.

**Frozen MCP tool contract** (13 tools; the UI may use ONLY the lifecycle six):
Granular (frozen, kept for direct/debug use): `check_recalls(product_key, serial?)`,
`verify_product(product_key, serial)` ← critical path · `get_inventory()`,
`get_device_state(device_id)`, `set_device_state(device_id, state)`,
`start_remedy(product_key, recall_number)`, `get_remedy_case(case_id)`
(renamed from `get_case` on 2026-09-27 — the name now belongs to the lifecycle surface).

Lifecycle (frozen 2026-09-27 — this is the UI's contract):
`start_case(product_key)` → runs to next user-input point (VERIFYING or terminal NO_MATCH)
`submit_verification(run_id, serial?, user_attested?)` → AWAITING_APPROVAL or terminal
`approve_action(run_id, action_id)` → scoped to the pending action only; wrong/stale
action_id rejected; on approval executes (verified) → remedy → TRACKING
`deny_action(run_id)` → ACTION_DECLINED · `get_case(run_id)` → run status ·
`get_events(run_id, after_seq?)` → frozen event feed `{"seq","from","to","at","payload"}`.

Layering (enforced): UI → business actions (lifecycle tools) → workflow engine →
state transitions → event feed. The UI never drives transitions directly; approval is
per-action (`disable_kitchen-air-fryer`), never a blanket yes; double-approval impossible.
Workflow runs are in-memory (server restart drops in-flight runs; remedy cases persist).

## Mac verification checklist (do NOT leave until demo week)

- [x] `server.py` starts on the Mac; Streamable HTTP round-trip works
      (`test_mcp.py` over `http://127.0.0.1:8000/mcp/` — verified on Mac)
- [x] `.venv/bin/python ui/tests/run_all.py` passes on the Mac with both local servers running and the backend freshly restarted (device ON; Python 3.11.2)
- [x] `pip install -r requirements.txt` works on the Mac's Python (3.11.2)
- [ ] Demo video recorded on the Mac against the local server

**Hackathon:** Amazon "Build, Ship, Shape" — Alexa+ track (1st: $25K cash)
**Deadline:** October 23, 2026, noon PDT — submit by Oct 21 for buffer
**Builder:** solo, AI-assisted. Budget **32–40 hours total** (~8–10 hrs/week). The plan is sized for this, not more.
**Mini-challenges:** AWS Builder (+$5K) is a *conditional* path — smallest meaningful AWS integration, only after the core works. Open Source (+$5K) is **not assumed**: it needs a separate new project or contribution alongside the primary submission; parked as optional.

---

## 1. Product thesis (frozen)

**RecallGuard is a household safety workflow agent that turns a recall signal into a verified, approval-gated resolution.**

The differentiator:

> **The agent knows when it does not have enough evidence to act.**

Evidence-aware escalation ladder:

```
uncertain match      → ask for serial/photo (gather evidence)
exact match          → explain why (show evidence)
consequential action → get approval (permission)
action complete      → verify state (confirm effect)
external workflow    → track completion (don't drop it)
```

---

## 2. Scope lock

```text
MUST HAVE
- live CPSC recall lookup
- 1 seeded household product
- candidate match
- ask for serial/photo when evidence is insufficient
- confirmed / no-match decision
- visible evidence pack
- explicit approval
- simulated ON → OFF → verified
- remedy draft
- persistent case state
- polished <3 min video

ONLY IF ABOVE WORKS
- smallest meaningful AWS integration (Bedrock/Strands/AgentCore) for AWS Builder mini
- polished Alexa-style web UI (beyond the basic simulated experience)
- model/serial extraction from photo (OCR)
- separate open-source mini-challenge project/contribution

DO NOT BUILD
- Health Canada scraping
- real smart plug / real hardware
- real manufacturer submission
- multiple product categories
- accounts/auth
- mobile app
```

---

## 3. Architecture (phased)

**Phase 1a — the gate (must work first):** CLI pipeline. One command hits CPSC, compares one stored product, outputs a verdict + evidence pack. No UI, no AWS, no polish until the gate passes.

**Phase 1b — track surface:** wrap the pipeline in a real MCP server (Python, FastMCP, spec 2025-11-25+, Streamable HTTP) + a minimal simulated Alexa+ web experience. The repo must genuinely import/call the track tech in code — not just mention it in the README.

**Phase 2 — only if Phase 1 is solid:** the smallest AWS integration that credibly qualifies for the AWS Builder mini-challenge (documented Bedrock/Strands/AgentCore use).

```
Phase 1a:  CLI ──→ CPSC API (keyless REST/JSON) ──→ verdict + evidence pack
Phase 1b:  web UI (simulated Alexa+) ──MCP──→ MCP server ──→ pipeline ──→ SQLite (inventory + cases)
                                                      └─→ simulated device endpoint (ON/OFF, labeled)
Phase 2:   + AWS layer (only if 1a/1b rock solid)
```

**CPSC API notes (verified):** `https://www.saferproducts.gov/RestWebServices/Recall?format=json` — no key. Quirks: no pagination (returns all matches; slice client-side), `RecallDescription` filter searches the Description field only, `RecallNumber` is the reliable lookup key.

---

## 4. State machine (the visible moat)

```
IDLE → SIGNAL_DETECTED → MATCH_REVIEW → VERIFYING → MATCH_CONFIRMED
   → EVIDENCE_READY → AWAITING_APPROVAL → ACTION_EXECUTED
   → REMEDY_STARTED → TRACKING → RESOLVED
                     ↘ NO_MATCH → IDLE (logged, explainable)
```

Every transition writes an **evidence pack**: recall number, CPSC link, matched fields, confidence (`CONFIRMED` / `LIKELY` / `NO_MATCH`), timestamp. Render the current state as a stepper in the UI — judges *see* the orchestration.

**Verification logic:** model matches recall's listed models → `LIKELY`, request serial. Serial corroborated by recall data → `CONFIRMED`. No match → stand down with an explanation (the "knows when it lacks evidence" moment — demo it briefly; it's a feature).

**Approval policy:** read-only actions need no approval; consequential actions (device OFF, remedy start) require explicit "yes". Never auto-submit anything external.

---

## 5. Demo script (under 3 minutes)

| Time | Beat |
|------|------|
| 0:00 | Hook: "Yesterday the CPSC published a recall. RecallGuard found it may affect your kitchen." |
| 0:25 | Signal → match: recall card, model matches — "I need the serial to confirm" |
| 0:55 | Verification: serial confirmed → evidence pack displayed |
| 1:25 | Explanation + approval: hazard, remedy, "the plug is ON — turn it off and draft the replacement request?" → "yes" |
| 1:55 | Action: `Kitchen Air Fryer: ON → OFF → verified` (labeled simulated) |
| 2:20 | Remedy: request drafted from manufacturer remedy data; case opened, "tracking until resolved" |
| 2:45 | End card: architecture, real (CPSC API, MCP server) vs simulated (device), repo link |

Pre-record. Never live-demo.

---

## 6. Week-by-week run (32–40 hr budget)

**Rule: weekly demo-or-cut.** Every Sunday the milestone runs end-to-end on video, or scope gets cut — never extended.

**Week 1 (Sep 28 – Oct 4, ~8–10h): the gate**
- Gate: `one command → CPSC → compare one stored air fryer → LIKELY / CONFIRMED / NO_MATCH + evidence`
- If the gate isn't clean by end of the first build session: no UI, no AWS, no polish. Fix the pipeline.
- Only after the gate: wrap in FastMCP server (Phase 1b start)
- Freeze one real air-fryer recall as the demo recall

**Week 2 (Oct 5 – Oct 11, ~8–10h): the workflow**
- State machine, verification flow, evidence pack rendering, approval gate, simulated device endpoint, persistent case state
- Minimal simulated Alexa+ web experience with visible state stepper
- Milestone: full loop runs locally, states visible

**Week 3 (Oct 12 – Oct 18, ~8–10h): harden + demo**
- Test the *exact* demo path repeatedly — break it, fix it, lock it
- Record demo video; draft product feedback (required field: what worked/didn't with MCP SDK, Alexa+ docs, CPSC API)
- Friction log maintained throughout (up to **10% judging bonus**)
- Milestone: final video recorded; repo has README + run instructions + license

**Week 4 (Oct 19 – Oct 21, ~4–6h): submit**
- Repo cleanup; Devpost submission (description, repo, video, product feedback, track: Alexa+)
- Submit by **Oct 21**

---

## 7. Judging-criteria mapping

| Criterion | How we hit it |
|---|---|
| Tech Implementation | Real MCP server (spec 2025-11-25+, Streamable HTTP) with track tech genuinely in code; live CPSC API integration |
| Design | One coherent flow, visible state stepper, honest simulated-vs-real labeling |
| Potential Impact | Every household owns recall-eligible products; recalls are fragmented and easy to miss |
| Quality of the Idea | Evidence-aware escalation, not a notifier; "knows when it lacks evidence" |

---

## 8. Submission checklist (from official rules)

- [ ] Text description of the project
- [ ] GitHub repo: all code + run instructions (public with license is fine; does **not** count as the Open Source mini entry)
- [ ] Demo video < 3 min, public, English, no copyrighted music
- [ ] Product feedback on **every** tool/API/SDK used (required field)
- [ ] Track selection: Alexa+
- [ ] Friction log attached (bonus)
- [ ] AWS Builder mini: only if Phase 2 happened — documented AWS integration
- [ ] Open Source mini: only if a *separate* project/contribution was shipped — do not assume

---

## 9. Friction log (start Week 1)

| Date | Task attempted | Expected | Actually happened | Severity | Workaround | Suggestion for Amazon |
|---|---|---|---|---|---|---|
| | | | | | | |

## 10. Risk register

| Risk | Mitigation |
|---|---|
| **Time (32–40h total) — biggest risk** | Scope lock §2; weekly demo-or-cut; Phase 2 is optional |
| CPSC API flaky/slow | Cache responses; demo uses frozen recall data |
| MCP spec/SDK drift | Pin versions Week 1; verify transport early |
| Demo failure | Pre-recorded video only; no live demo |
| Scope creep | §2 DO NOT BUILD list; park everything else in v2 |
| "Just another recall lookup" perception | Lead every pitch with the escalation ladder, not the API |

---

## 11. Open questions

- Smallest AWS integration that credibly qualifies for AWS Builder mini — decide only if Phase 1 is solid (candidates: Bedrock for the explanation step, or Strands for orchestration).
- Whether to attempt a separate Open Source mini entry at all — decide in Week 3; never at the expense of the primary submission.
