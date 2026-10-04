# Product feedback draft

The current Devpost rules ask for product feedback on each tool/API/SDK: what it was used for, what worked, what needs work, onboarding, and whether you would use it again. Keep the AWS answers marked as pending until a real call is measured.

## Model Context Protocol / FastMCP — Alexa+ track

- **Used for:** The local RecallGuard server exposes a frozen business-action lifecycle over Streamable HTTP. The web UI consumes the six lifecycle tools; the workflow owns state transitions.
- **What worked:** The in-process and live HTTP test paths made it possible to validate the same contract, including exact action IDs, event polling, and safe refusal from terminal states.
- **What needs work:** A stale `test_mcp.py` continued checking the old surface after the lifecycle contract was frozen. It was easy for obsolete coverage to look like a backend regression until the test was migrated.
- **Onboarding:** FastMCP made a local Streamable HTTP server straightforward to run after the Python environment and Mac certificate bundle were set up. The first Mac transport check also encountered sandbox localhost restrictions.
- **Use again?** Yes. It provided a real protocol boundary and made the UI/backend separation testable. Keep the frozen contract and HTTP test as the source of truth.

## U.S. CPSC recall API

- **Used for:** Live recall lookup for one seeded Insignia air fryer and a no-match vacuum path.
- **What worked:** Keyless JSON lookup returned the real 2024 recall #24159 and enough data to identify a likely model match.
- **What needs work:** The returned recall did not list serial numbers, so live data could not verify a specific unit. Query-field behavior and the shape/completeness of returned fields took direct testing to understand.
- **Onboarding:** No credentials were needed; the main work was learning which fields were searchable and treating missing fields as missing evidence.
- **Use again?** Yes, as an evidence source. Do not treat a model match as proof of serial-level applicability.

## Amazon Bedrock Converse / Boto3 — AWS Builder mini-challenge

- **Used for:** An optional one-request explanation of workflow-provided CPSC facts. The model has no tools or authority over evidence sufficiency, approvals, or device actions.
- **What worked:** The request boundary is small, the output is capped, the facts are curated from backend events, and mocked tests verify the safe failure response.
- **What needs work:** **Pending live setup.** This Mac has no usable AWS profile, credentials, region, or model ID, so no live call or latency measurement has been completed. Do not claim the live integration is verified.
- **Onboarding:** Blocked before the first call by missing local AWS profile and Bedrock configuration. After setup, record the exact model/region and one-call latency without publishing account or credential details.
- **Use again?** Pending. Decide after the live call and fallback check.

## Browser UI / Node test stack

- **Used for:** A responsive local web experience that restores the backend case, polls the event feed, and tests state-dependent rendering and approval visibility.
- **What worked:** No frontend build/install step was needed; the UI tests cover restoration, stale runs, approval visibility, and prevention of fabricated transitions.
- **What needs work:** Local HTTP testing can be blocked by sandbox networking restrictions, which need to be surfaced to the developer.
- **Onboarding:** Start the Python UI and MCP HTTP servers; Node is needed only for the state/UI tests. The ordered test script captures the setup sequence.
- **Use again?** Yes. It made a complicated stateful MCP flow visible without requiring Alexa+ preview-only developer tools.

## AWS Builder positioning note

The official judging rubric explicitly calls a single Bedrock text-generation call “obvious,” while naming a multi-service pipeline or agentic architecture as more creative. The Bedrock explainer may satisfy the documented integration requirement, but do not pitch it as the standout AWS Builder innovation. RecallGuard’s stronger case is the Alexa+ workflow and evidence-aware safety behavior; avoid adding services just to chase a second prize.
