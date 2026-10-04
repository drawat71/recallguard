# RecallGuard demo script — 2:55 target

**Core line:** “RecallGuard knows when it lacks enough evidence to act.”

## Preflight

- Start the Mac UI and MCP HTTP server; reload the browser and confirm `MCP connected`.
- Confirm the simulated device reports ON. Keep the backend freshly restarted before recording.
- Use the seeded Insignia NS-AF5DSS2 air fryer and CPSC recall #24159. Do not enter a real serial number; the demo uses the label attestation.
- Confirm the Bedrock profile, region, and model are configured if showing the optional explanation. If unavailable, omit that click and keep the main workflow unchanged.
- Close notifications and unrelated tabs. Keep the browser at the app’s normal desktop size.

## Timed path

| Time | Screen action | Narration |
|---|---|---|
| 0:00–0:12 | Show the ready screen. | “A recall alert is only useful if you can tell whether it applies to your home. RecallGuard knows when it lacks enough evidence to act.” |
| 0:12–0:32 | Click **Check my air fryer**. Let the backend return LIKELY and show CPSC #24159. | “The model matches a real CPSC recall. But CPSC does not publish serials for this recall, so model match alone is not proof.” |
| 0:32–0:48 | Point to matched model, missing serial, and VERIFYING. | “RecallGuard stops here and asks for evidence. It does not quietly turn uncertainty into approval.” |
| 0:48–1:00 | If live Bedrock is configured, click **Explain this evidence** and show the observed explanation. If not, hold on the missing-evidence card and point out that no explanation can fill in a missing serial. | “Bedrock can explain the evidence in plain language. It cannot change the verdict, clear the evidence gate, or approve anything.” |
| 1:00–1:22 | Attest to checking the physical label and submit. Review the exact pending action. | “The person checks the rating label. The backend records that as an attestation, not as serial verification.” |
| 1:22–1:38 | Approve the displayed `disable_kitchen-air-fryer` action. | “Only now does RecallGuard ask permission for this exact action.” |
| 1:38–1:55 | Show device ON → OFF → verified, remedy draft, and TRACKING. | “The simulated plug reports OFF, RecallGuard reads it back, and a remedy case is opened for tracking. The device endpoint is simulated; the recall data and workflow are real.” |
| 1:55–2:13 | Start a fresh case and choose **I can’t verify the label**. | “If the label cannot be verified, the case ends in INSUFFICIENT_EVIDENCE. The device stays on and approval is unavailable.” |
| 2:13–2:26 | Choose **No-match demo**. | “A clean no-match stands down with its evidence trail.” |
| 2:26–2:42 | Start the likely case, attest, then deny the exact action. | “Even with enough evidence to propose an action, the user can deny it. The workflow records the denial and does not switch the device.” |
| 2:42–2:55 | End on event trail and the real/simulated labels. | “Real recall. Honest uncertainty. Explicit permission. Verified action. That is RecallGuard.” |

## Recording rules

- Record the actual UI and backend responses; do not stage or edit workflow events.
- The happy path may use the same CPSC result throughout one run. For subsequent paths, use the UI’s own fresh-case controls.
- If a live CPSC call is slow, pause before recording and confirm connectivity; do not cut out a missing state transition.
- If live Bedrock is unavailable, use the missing-evidence card for that 12-second beat. Keep the explanation layer out of the recording. Never imply a mocked response came from AWS.
- Target 2:45–2:55. Leave the last few seconds for the final line rather than rushing the evidence and approval steps.
