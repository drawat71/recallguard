# RecallGuard — Devpost draft

## RecallGuard knows when it lacks enough evidence to act.

Product recalls are easy to miss and hard to apply to a specific item in your home. A model name can look like a match while the serial-level evidence is missing. Most alert systems stop at the notification. RecallGuard turns that uncertainty into a safe, auditable workflow.

RecallGuard checks live U.S. Consumer Product Safety Commission recall data, compares the result with a household product, and shows the evidence behind a likely match. When the recall does not provide serial numbers, the workflow says so and asks the user to inspect the product label. If evidence is insufficient, it stands down. If the user verifies the label, RecallGuard presents one exact action for approval. After approval, it changes a simulated smart-home device state, reads the state back, opens a remedy case, and tracks the result in an event trail.

The demo uses a real CPSC recall for an Insignia air fryer. The CPSC lookup, MCP server, lifecycle workflow, approval checks, and remedy tracking run locally against live recall data. The home device endpoint is a simulation; it is clearly labeled and is not connected to real hardware. RecallGuard does not submit a claim to a manufacturer.

An optional Amazon Bedrock feature explains backend-provided evidence in plain language. It is an explanation layer only: matching, evidence sufficiency, approval, and action remain deterministic workflow decisions. If Bedrock is unavailable, the case continues unchanged and the UI reports the fallback.

**Built with:** Python, FastMCP over Streamable HTTP, a local web UI, live CPSC data, and an optional Amazon Bedrock Converse call.

**The point:** an agent should know when it does not know enough—and prove that it waited.

## 30-second version

“RecallGuard turns a recall alert into a verified household-safety workflow. It finds a likely match in real CPSC data, shows what is missing, and stops when the evidence is not enough. After a person checks the label and approves one exact action, RecallGuard verifies a simulated device change and tracks the remedy. Bedrock can explain the evidence, but deterministic gates own every decision.”

## Submission checks before posting

- Replace this note with the measured Bedrock result only if live inference was actually completed.
- Add the final public demo-video link and repository link.
- Confirm the current challenge name, eligibility, required disclosures, and word limits against the official submission page before posting.
