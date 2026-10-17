# Submission checklist — Build, Ship, Shape

Current official deadline: **October 23, 2026 at 12:00 p.m. PDT**. Keep October 21 as the internal cutoff. Recheck the organizer page before final submission.

| Requirement | Status | Next step |
|---|---|---|
| Alexa+ track: working MCP server over Streamable HTTP | Verified on Mac; full repo gate passed | Keep the final test output and current setup instructions with the repo. |
| Working project and setup instructions in a GitHub repository | Private repository: https://github.com/drawat71/recallguard | Before submission, grant the required reviewers access or make the repository public with an open-source license. |
| English project description | Draft ready | Finalize against actual completed Bedrock status and add repository/video links. |
| Demo video, less than 3 minutes, publicly visible on YouTube or Vimeo | Not recorded | Use the 2:55 script, record the actual UI, and upload only after reviewing the rules below. |
| Product feedback for every tool/API/SDK | Draft ready | Complete the AWS section after the live inference; submit what worked, what needs work, onboarding, and whether you would use it again. |
| Identify primary track and mini-challenges | Pending submission form | Select Alexa+. Select AWS Builder only if the Bedrock integration is documented and honestly represented. |
| Friction log | Draft ready | Review each entry for accuracy, severity, and steps before attaching. |
| Video marks and rights | Needs organizer/user review | The current UI shows product-brand and recall names. Official rules say video must not include third-party trademarks or copyrighted material without permission; clarify whether factual/nominative product references are acceptable before publishing. |
| Live Bedrock call and measured latency | Blocked on AWS setup | Configure an authorized local profile, Bedrock-enabled region, and model ID; run the one-shot helper. Never send credentials in chat. |

The current rules require a video shorter than three minutes, publicly accessible on YouTube or Vimeo, in English, with no third-party trademarks or copyrighted media absent permission. They also say that one Bedrock text-generation call is an “obvious” AWS Builder entry, while more creative examples use multi-service or agentic architecture. The present Bedrock explainer may meet the documented-integration threshold, but it is not a strong standalone AWS Builder differentiator. Keep the product frozen and make the Alexa+ safety-workflow story the lead.
