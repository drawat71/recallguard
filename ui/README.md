# RecallGuard demo UI

A browser-native, responsive safety workspace connected to the real RecallGuard lifecycle over MCP Streamable HTTP. Application changes are isolated to `ui/`; the original backend and tests are unchanged.

## Run locally

From the repository root (Python 3.11 tested):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python ui/run.py
```

Open **http://127.0.0.1:3000**. Ctrl-C stops both servers. No frontend install/build is needed. Node 18+ is only needed for the JavaScript tests (Node 26 tested).

The launcher starts the original backend on `127.0.0.1:8000` and the UI adapter on `127.0.0.1:3000`. On macOS it uses `/etc/ssl/cert.pem` when no certificate override is already set; certificate verification stays enabled. This fixes the missing certificate bundle on the tested Mac's Python 3.11.2.

For separate terminals:

```sh
# Terminal 1, macOS
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python server.py
# Terminal 2
.venv/bin/python ui/bridge.py
```

## Four demo paths

1. **Happy:** Check my air fryer → enter the serial → explicitly check the rating-label attestation → Submit evidence → review the exact proposed action → Approve action. The backend produces the device read-back, remedy draft, and TRACKING state. For a staged demo only, use a clearly fictional serial such as `DEMO-SN88412`. Attestation is labelled as user evidence, not independent CPSC serial confirmation.
2. **Insufficient evidence:** New air fryer check → I can't verify the label. Ends at INSUFFICIENT_EVIDENCE, with no approval controls or device action.
3. **No match:** No-match demo. Uses the handoff's existing `bedroom-vacuum` control, searches live data, and ends at NO_MATCH. No product management or multi-product scope was added.
4. **Deny:** Start and verify an air fryer case → Deny action. Ends at ACTION_DECLINED with no device action or remedy in that case.

Reload at verification, approval, or completion to restore the current case through `get_case` and `get_events`. Raw event payloads expand in the evidence trail. Only the run ID and first-event fingerprint are saved locally; label inputs are not persisted.

**For a fresh ON → OFF recording, restart the backend first.** The backend has one shared simulated device, so later approvals truthfully show OFF → OFF. The UI has no reset-device shortcut and never calls a low-level device tool. Restarting drops in-memory workflow runs; remedy drafts persist in the existing `cases.json` store. A saved run ID reused by the restarted backend is rejected during restore or before action.

## Connection and architecture

Browser → same-origin `/api/<tool>` JSON adapter → FastMCP Client → actual HTTP MCP server → original workflow.

The adapter allowlist is exactly:

- `start_case(product_key)`
- `submit_verification(run_id, serial?, user_attested?)`
- `approve_action(run_id, action_id)`
- `deny_action(run_id)` — the actual frozen contract has no action_id here
- `get_case(run_id)`
- `get_events(run_id, after_seq?)`

Initial event fetch uses `after_seq: -1`, because the first event is sequence zero. Subsequent fetches use the last received sequence. The UI renders event order and timestamps as returned; it does not replay or fabricate backend transitions. A current-state snapshot is reconciled with the event count before enabling controls. Approval rereads the case, validates run identity, and sends the exact action ID the user reviewed. A changed ID requires another review. Terminal states suppress stale pending actions.

Errors block action controls; Refresh case reconciles an uncertain result. Actions are never automatically retried. The adapter is localhost-only, rejects unrelated browser origins, validates the contract, and forwards no arbitrary URLs. There is no AWS, auth, real hardware, photo processing, or manufacturer submission.

## Honest limits of the frozen handoff

- Initial lifecycle events do not report device state on insufficient-evidence/no-match paths. The UI says **Not reported / no device action**, not an invented ON. The untouched workflow regression verifies the device remains ON in a fresh insufficient-evidence run.
- Detailed hazard evidence appears only after verification. The current recall payload has a null remedy field; the draft uses the backend's “see recall notice” fallback. The UI preserves that rather than writing a remedy itself.
- Lifecycle events omit the original CPSC URL. The UI offers a labelled CPSC search for the returned recall number.
- Confirmation based on attestation does not prove serial corroboration. The original evidence text and the actual confirmation basis are both visible.
- The backend writes local remedy drafts and marks them TRACKING. There is no external status polling, manufacturer submission, or resolution transition.
- Voice and photo verification are not implemented. This is an Alexa-style text demo.
- Live CPSC availability is required; no fixture/offline fallback is silently substituted.

## Tests

For a single ordered gate covering all backend, UI, and MCP HTTP tests, keep both local servers running via `ui/run.py`. Restart `server.py` first so the simulated device begins ON; the HTTP happy path verifies ON → OFF. Then run:

```sh
.venv/bin/python ui/tests/run_all.py
```

The runner sets the Mac certificate bundle for Python when needed. It runs the MCP transport happy path first, then the UI-adapter HTTP paths, original protocol/lifecycle/workflow tests, the live CLI check, and the adapter and browser-state unit tests. Live CPSC availability is required. The HTTP tests create local workflow/remedy cases and leave the shared simulated device OFF after success; restart the backend before another fresh run.

Individual offline/UI checks:

```sh
node --test ui/tests/*.test.js
.venv/bin/python -m unittest ui.tests.test_bridge
```

The migrated `test_mcp.py` covers the frozen 13-tool surface through real Streamable HTTP, including all lifecycle outcomes, exact-action checks, restoration, and incremental event polling. `ui/tests/live_http.py` independently checks the four UI paths through the local adapter and real MCP server.

See `VALIDATION.md` for results and `IMPLEMENTATION_PLAN.md` for the pre-code plan.

## Optional AWS Builder integration

The optional **Explain this evidence** panel uses Amazon Bedrock Converse once, only after a person presses the button. It provides a short explanation of CPSC recall facts already returned by the lifecycle. It has no tools, cannot inspect or change the case, cannot control a device, and cannot approve or deny an action. Backend state, match evidence, and deterministic approval gates remain authoritative.

The sidecar sends only a curated JSON set of public recall facts, hazard/remedy text, the backend verdict, and the reported confirmation basis. It excludes the run ID, event timestamps, raw event payloads, serial numbers, and device IDs. The panel identifies AWS as the destination and explains which data is sent before the request. Nothing is sent until the person presses the button. The existing six-tool MCP contract is unchanged; the UI's separate same-origin explanation route accepts only the current run ID and rebuilds the prompt from the real backend event feed.

To enable it, install the separate optional SDK and use your existing AWS profile/role, model access, and region:

```sh
.venv/bin/python -m pip install -r ui/aws/requirements.txt
export AWS_PROFILE=your-existing-profile
export AWS_REGION=us-west-2
export RECALLGUARD_BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
.venv/bin/python ui/run.py
```

Change the model ID or region to one enabled for your account. The model ID defaults to no value; with no configuration, the optional button returns setup guidance and leaves the workflow unaffected. Use least-privilege `bedrock:InvokeModel` permission for the selected model or inference profile. Each click makes at most one synchronous request, capped at 180 output tokens with SDK retries disabled. AWS account usage may incur inference charges. See [AWS's Boto3 Converse example](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-ex-con.html), [model availability and compatibility](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html), and [inference permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.html).

Bedrock was tested here with a mocked Converse client and prompt/fact-boundary tests. No AWS credentials were configured, so no paid live inference was sent. Strands was not added: this single bounded explanation call needs no agent or tools, and an autonomous layer would add risk without improving this step.

The all-in-one gate also runs the mocked AWS boundary tests. No Bedrock model access or live AWS credential is required to run the core or test suites.
