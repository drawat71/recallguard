# One live Bedrock check — pending AWS setup

The application has no usable AWS profile or credentials on this Mac, no region, and no model ID configured. The live inference and its latency therefore remain **unverified**. Do not paste access keys, SSO tokens, account IDs, or secret config into chat.

## When a permitted profile is available

Use a profile whose role can call Bedrock Converse for one approved model. Confirm the model is enabled in the chosen region. Keep the public recall fact set already returned by the local workflow; the one-shot helper never accepts a serial or arbitrary prompt.

```sh
set -o pipefail
AWS_PROFILE=your-profile \
AWS_REGION=your-bedrock-region \
RECALLGUARD_BEDROCK_MODEL_ID=your-enabled-model-id \
.venv/bin/python submission/bedrock_live_check.py WF-0001 \
  | tee submission/live_bedrock_result.json
```

Replace `WF-0001` with the active local run ID. The helper fetches `get_case` and `get_events` before timing. It reports the Converse-call latency and returned explanation as JSON. Record whether the output correctly describes a LIKELY model match and missing serial evidence; it must not claim the device is verified or that RecallGuard approved an action.

The request is capped at 180 output tokens, temperature 0.2, and one SDK attempt. Use a Bedrock-enabled region and a model that supports Converse. Inference may incur AWS charges. AWS documents the [Boto3 Converse flow](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-ex-python.html), [model access requirements](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html), and [inference permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.html).

## Fallback check

The no-configuration fallback was verified in the browser: it displayed setup guidance and kept the current case at VERIFYING. The mocked Bedrock failure test also verifies a generic provider error becomes a safe `Bedrock is temporarily unavailable` response. Re-run these local checks after the live call:

```sh
.venv/bin/python -m unittest ui.aws.test_bedrock_explanation ui.tests.test_bridge
```

That failure check is deliberately mocked. Do not label it a live AWS outage test. A live unavailable-model request would be an additional AWS call and is not needed to validate the deterministic application fallback.
