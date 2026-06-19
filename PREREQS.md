# Workshop Prerequisites

Please complete these **before** the session — the first 30 minutes assume you can already deploy an agent.

## Required

- [ ] **Anthropic API key** with the Managed Agents beta enabled
  - Confirm: `curl -s https://api.anthropic.com/v1/agents -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "anthropic-beta: managed-agents-2026-04-01"` returns `{"data": [...]}`, not a 403/404
  - If you get `beta feature not enabled`, ask your Anthropic contact to enable `managed-agents-2026-04-01` on your org
- [ ] **Console access** at https://platform.claude.com — you should see a "Managed Agents" tab in your workspace
- [ ] **Python 3.10+** with `pyyaml` + `requests` — use a venv (modern macOS/Linux block system pip via PEP 668):
  ```
  python3 -m venv .venv && .venv/bin/pip install pyyaml requests
  ```
  Then run scripts as `.venv/bin/python3 deploy.py ...` (or `source .venv/bin/activate` first)
- [ ] **Clone this repo**: `git clone https://github.com/cam-karagitz/cma-insurance-workshop && cd cma-insurance-workshop`
- [ ] **Verify the kit**: `python deploy.py --dry-run examples/claims/fnol-triage.yaml` — should print a JSON request body, no errors
- [ ] Confirm **outcomes** and **multiagent** are enabled on your org (separate from the managed-agents beta — ask your Anthropic contact). Labs 3+ depend on these.

## Recommended

- [ ] **Claude Code** installed: `npm i -g @anthropic-ai/claude-code` — opening this repo in CC loads `CLAUDE.md` and makes your session CMA-aware
- [ ] Run `/claude-api managed-agents-onboard` in Claude Code once before the workshop — it scaffolds a hello-world agent in your language and walks the 4-resource model. Takes ~5 minutes; we'll skip it on the day if you've done it.

## What to bring (optional, for the "swap in your own MCP" segment)

- The URL of any **streamable-HTTP MCP server** you already have (policy admin, claims, rating, CRM)
- Or nothing — the examples ship with hosted mocks that work out of the box

## If something's blocked

Reply-all to the calendar invite with the error output and we'll sort it before the day.
