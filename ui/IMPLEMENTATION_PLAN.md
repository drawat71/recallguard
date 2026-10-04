# Isolated UI implementation plan

Source of truth: ../BUILD_PLAN.md and ../CODEX_UI_PACKAGE.md, checked against the actual server and workflow. All application edits stay in ui/. Backend source and original tests remain byte-for-byte unchanged.

1. Serve a browser-native frontend and a same-origin JSON adapter on localhost:3000. The adapter uses FastMCP Client over Streamable HTTP to localhost:8000/mcp/. Allow only the frozen six lifecycle tools and their arguments. No workflow imports, state mutation, or low-level device tools.
2. Render a calm, polished safety workspace: simulated Alexa-style conversation, event-derived workflow stepper, recall evidence and provenance, manual serial/unchecked attestation, exact pending-action approval/deny, simulated device readings, remedy draft, inspectable raw events.
3. Persist only the run ID and first-event identity in browser storage. Restore through get_case and get_events(-1); reject recycled IDs after a backend restart. Poll get_events incrementally; reconcile with get_case. No optimistic state transitions or replay animation suggesting actions are happening later than they did.
4. Cover all four required paths. The no-match control uses the already seeded bedroom-vacuum solely as a demo control, not a product-management feature.
5. Test state rendering, terminal approval suppression (including stale pending actions), exact approval IDs, sequence-zero inclusion, restore, network errors, adapter allowlist, live HTTP lifecycle, and existing backend suites. The original test_mcp.py was migrated to the frozen HTTP contract; no test is intentionally left failing.

## Contract observations

- deny_action accepts run_id only in both authoritative docs and implementation.
- Sequence numbering starts at zero; get_events defaults to after_seq=0, so explicitly request -1 initially.
- Backend keeps pending_action after terminal completion; UI must gate controls on state AND terminal AND pending_action.
- Lifecycle events do not expose initial device state for insufficient evidence or no-match. Display not reported/no action taken, never assume ON. A previous run may already have switched the shared simulated device OFF.
- CPSC URL and detailed hazard/remedy are not all present in early events. Show only supplied evidence; link a clearly labelled CPSC search derived from recall number, not a fabricated source URL.
- Attestation is a separate basis from serial corroboration. Render basis verbatim.
- Workflow runs are in-memory and run IDs recycle after restart. Compare first event identity before restoring or acting on a saved run.
- Completed: test_mcp.py now covers the frozen 13-tool surface over HTTP and retains the ON → OFF transport assertion.

## Delivery addition

Added ui/run.py as a one-command launcher for the two existing local processes, including the verified macOS certificate-bundle configuration. Added ui/VALIDATION.md and ui/tests/run_all.py. The single ordered validation gate passed in full, including the current-contract MCP HTTP test.
