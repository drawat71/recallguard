# Codex work package: RecallGuard demo video

## Objective

Produce the submission demo video by recording the **real UI** driven through
the **real backend**, timed to the existing script. Deliver two cuts:
a silent timed cut (for a human voiceover) and a TTS-narrated cut.

Target **2:45–2:55**, hard cap **under 3:00** (organizer rule).

## Inputs (read first, do not modify)

- `submission/demo_script.md` — the beats, timings, and exact narration lines.
  This package executes that script; it does not rewrite it.
- `submission/submission_checklist.md` — the video rules (public YouTube/Vimeo,
  English, < 3 min, no third-party media without permission).

## Setup

```bash
# from the repo root, fresh venv already installed
RECALLGUARD_FROZEN=1 python ui/run.py
# backend on :8000, UI on http://127.0.0.1:3000
```

- **Always record with `RECALLGUARD_FROZEN=1`.** The backend then serves the
  captured CPSC snapshot (recall #24159) instead of live data — deterministic
  takes, no mid-recording lookup flakiness. The script explicitly permits
  reusing the same CPSC result through one run.
- Freshly restart both servers before recording (script preflight).
- Confirm before the take: UI shows `MCP connected`, simulated device is ON.
- Close notifications and unrelated tabs. Desktop browser size, 1080p capture.

## Paths to record (in script order)

1. **Happy path** — Check my air fryer → LIKELY + CPSC #24159 → VERIFYING with
   the missing-serial card → attest the physical label → review the exact
   pending action → approve `disable_kitchen-air-fryer` → device
   ON → OFF → verified → remedy draft → TRACKING.
2. **Insufficient evidence** — fresh case → "I can't verify the label" →
   INSUFFICIENT_EVIDENCE. Device stays ON; **no approval control exists**.
3. **No-match** — the UI's no-match demo path → clean stand-down with its
   evidence trail.
4. **Deny** — fresh likely case → attest → **deny** the exact action →
   denial recorded, device not switched.
5. **Close** — end on the event trail with the real/simulated labels visible.

**Bedrock beat (0:48–1:00): SKIP IT** unless a live Bedrock profile/region/model
is already configured on this machine. Default: hold on the missing-evidence
card for that beat, exactly as the script's fallback specifies. Never render
or imply a mocked Bedrock response.

## Recording method

- Drive the real UI in a real browser (e.g. Playwright + Chromium) and capture
  video. Click the actual controls; type nothing fake.
- Advance on **UI state, not fixed sleeps**: wait until the expected state text
  / stepper position is visible before the next action, then hold each beat
  for its scripted duration so narration fits.
- **Never cut out a state transition** (script rule). If a beat runs long,
  extend a hold, not a cut.
- No board/puck footage. No music, no stock media, no third-party assets.

## Narration

- **Cut A (silent):** video only, beats timed to the narration lines in the
  script. This is the cut Dish can voice over himself.
- **Cut B (TTS):** same video with narration generated from the script's exact
  lines (e.g. macOS `say` → audio track, muxed with ffmpeg), aligned to the
  beat table. Do not paraphrase the lines.
- Report both durations (`ffprobe`). If Cut B's TTS timing drifts >5s from a
  beat boundary, adjust hold lengths and re-render rather than speeding speech.

## Non-goals

- No changes to the backend, `ui/`, the frozen contracts, or
  `submission/demo_script.md`. Recording tooling lives in a new `demo/` dir.
- No YouTube/Vimeo upload — Dish uploads after review.
- No Bedrock live call or AWS setup (separate decision).
- No staging: every workflow event on screen must come from the backend.

## Files you may touch

- New directory `demo/` only (recording script, outputs, run log).

## Acceptance criteria

1. `demo/output/recallguard-demo-silent.mp4` and
   `demo/output/recallguard-demo-narrated.mp4` exist; each is 2:45–2:55,
   1080p, playable start to finish.
2. All four paths appear in script order with **every** state transition
   visible — including the verified ON → OFF read-back and TRACKING.
3. The approval beat visibly shows approving the exact pending action
   `disable_kitchen-air-fryer` — not a generic yes.
4. Stand-down paths (insufficient evidence, no-match, deny) show no approval
   being taken and the device state unchanged.
5. Run log in `demo/` records: frozen mode on, servers freshly restarted,
   preflight checks passed, and the take's path timings.
6. Backend and UI test gates still pass, untouched:
   `.venv/bin/python ui/tests/run_all.py` exits 0.
