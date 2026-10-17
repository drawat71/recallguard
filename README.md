# RecallGuard

RecallGuard checks live U.S. CPSC recall data, gathers evidence, and asks before taking a consequential action. Its central rule is: **RecallGuard knows when it lacks enough evidence to act.**

This project implements a self-hosted MCP server over Streamable HTTP and a browser demo connected to its frozen lifecycle API. Device control is simulated. The workflow and event feed—not the optional language model—own evidence sufficiency, approval, and action.

## Run locally

Tested on macOS with Python 3.11 and Node 26. From this folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python ui/run.py
```

Open <http://127.0.0.1:3000>. The launcher starts the UI on port 3000 and MCP on port 8000. The CPSC integration needs network access. On macOS, the launcher selects the system certificate bundle when needed.

## Tests

For the full backend, UI, and live MCP HTTP gate, restart the backend first so the simulated device starts ON, keep both servers running, then run:

```sh
.venv/bin/python ui/tests/run_all.py
```

The live CPSC endpoints are used by some checks. See [ui/README.md](ui/README.md) for the four paths, frozen API, and detailed test setup.

## Optional Amazon Bedrock explanation

The Bedrock button makes one bounded explanation request only when configured and clicked. It cannot change workflow state, verification, approval, or device behavior. Configure an existing AWS profile, region, and Converse-capable model locally; never commit credentials or generated AWS result files. See [ui/README.md](ui/README.md) and [submission/bedrock_live_check.md](submission/bedrock_live_check.md).

## Demo and submission material

The [submission](submission/) folder contains the demo script, product feedback and friction-log drafts, judge Q&A, and architecture / real-versus-simulated slides. The current demo flow targets 2:55. Review the current hackathon rules before publishing a repository or video.

## Repository access

The repository is private at [drawat71/recallguard](https://github.com/drawat71/recallguard). On another machine, sign in to GitHub with an account that has access, then clone it:

```sh
gh repo clone drawat71/recallguard
cd recallguard
```

Follow the local setup above to create a fresh virtual environment on that machine. Generated case data, local environments, preview images, and packaging ZIPs are excluded by `.gitignore`.
