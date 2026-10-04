# Judge Q&A — grounded in the current repo

## What is the core idea?

RecallGuard knows when it lacks enough evidence to act. A likely product-model match is not treated as proof about a specific item. The workflow asks for evidence or stands down.

## What happens if the model hallucinates?

The optional Bedrock component only explains facts already returned by the workflow. It cannot set a verdict, change state, satisfy verification, approve an action, or operate the device. The workflow owns those gates. If Bedrock returns an error or empty response, the UI reports that the explanation is unavailable and leaves the case unchanged.

## What exactly is real?

The CPSC recall lookup, FastMCP Streamable HTTP server, lifecycle workflow, event feed, approval checks, and remedy-case tracking are real software paths exercised by the tests. The recalled-product information comes from CPSC data.

## What is simulated?

The smart-home endpoint is a local simulator. It reports the seeded device state, changes it from ON to OFF only after approval, and supports a read-back check. There is no real plug, no hardware command, and no manufacturer submission.

## Why ask the user to inspect the label?

Recall #24159 matches the seeded model but does not publish serial-level data in the returned record. The workflow keeps the result at LIKELY and distinguishes a user's label attestation from independent serial corroboration.

## Why not let Bedrock decide whether to act?

That would make the safety gate depend on a probabilistic explanation. The product thesis requires deterministic ownership of evidence sufficiency, approval, and action. Bedrock can make the evidence easier to understand without gaining authority over the case.

## What if the user cannot verify the label?

The workflow enters terminal `INSUFFICIENT_EVIDENCE`. Approval and remedy actions are rejected, and the simulated device remains ON.

## Can the user reject the action?

Yes. Approval names the exact pending action ID. A stale or incorrect ID is rejected, duplicate approval is blocked, and a deny is recorded as `ACTION_DECLINED` without executing the action.

## How do you prevent the UI from inventing states?

The UI sends lifecycle business actions only. It restores a run with `get_case`, renders events from `get_events`, and updates from the backend feed. It has no tool or API for setting workflow state directly.

## What happens if Bedrock is down?

The explanation request fails safely with a clear message. The workflow case is unchanged. The live AWS failure fallback should be described as verified only after the live call and a deliberate service-error test are both recorded.

## Is Bedrock live in this build?

The optional Boto3 Converse path is implemented and unit-tested with a mock. As of this validation, this Mac has no usable AWS profile, credentials, region, or model ID, so live inference has not yet been measured.

## What did you test?

The ordered local gate passed the MCP Streamable HTTP contract, UI-to-MCP HTTP adapter, protocol, lifecycle, workflow, backend checks, eight Python adapter/Bedrock tests, and fourteen JavaScript UI/state tests. The browser also exercised the live likely-match and safe Bedrock-not-configured fallback. A live Bedrock request remains pending AWS setup.

## What would you add next?

Nothing to the core flow for this submission. First record the three-minute demo and submit the evidence already in the repo. Any additional product scope would dilute the story and create new failure points.
