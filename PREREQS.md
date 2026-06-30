# Workshop Prerequisites

Please complete these **before** the session — the first 30 minutes assume you can already deploy an agent.

## Required

- [ ] **Anthropic API key** with the Managed Agents beta enabled
  - Confirm: `curl -s https://api.anthropic.com/v1/agents -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "anthropic-beta: managed-agents-2026-04-01"` returns `{"data": [...]}`, not a 403/404
  - If you get `beta feature not enabled`, ask your Anthropic contact to enable `managed-agents-2026-04-01` on your org
- [ ] **Console access** at https://platform.claude.com — you should see a "Managed Agents" tab in your workspace
- [ ] **Network reachability — checked from the network you will actually be on during the workshop** (corporate Wi-Fi / VPN, not a phone hotspot). Corporate proxies sometimes block one of these, and finding out on the day costs you the first lab:
  - `https://platform.claude.com` opens in your browser
  - `https://ins-mocks.vercel.app/` opens in your browser — that page lists the hosted mock insurance systems the examples call (all data is synthetic)
  - the API-key `curl` above returns JSON, which also proves `api.anthropic.com` is reachable
  - If any of the three is blocked, ask your network team to allow `api.anthropic.com`, `platform.claude.com`, and `ins-mocks.vercel.app` over HTTPS (443), and reply to the invite so we know before the day.
  - *Why this is only about your laptop:* the agents you'll build run in **Anthropic's cloud** and call the mock MCP servers from there — your corporate network is not in that path and cannot break the agents. This check covers your local tooling (`deploy.py`, `run.py`, `validate.py`) and the Console.
- [ ] **Python 3.10+** with `pyyaml` + `requests` — use a venv (modern macOS/Linux block system pip via PEP 668):
  ```
  python3 -m venv .venv && .venv/bin/pip install pyyaml requests
  ```
  Then run scripts as `.venv/bin/python3 deploy.py ...` (or `source .venv/bin/activate` first)
- [ ] **Clone this repo**: `git clone https://github.com/cam-karagitz/cma-insurance-workshop && cd cma-insurance-workshop`
- [ ] **Verify the kit**, three commands — in this order, from the repo root, using the venv python you just created (so you are testing the thing you will actually run with):
  - `.venv/bin/python3 -c "import yaml, requests; print('deps OK')"` — must print `deps OK`. This is the one that bites people: `deploy.py --dry-run` works WITHOUT `requests` (it never touches the network), so everything looks fine right up until your first REAL deploy dies with `ModuleNotFoundError`. Two seconds here saves your first lab.
  - `.venv/bin/python3 deploy.py --dry-run examples/claims/fnol-triage.yaml` — prints a JSON request body, no errors (offline; proves the tooling works)
  - `.venv/bin/python3 validate.py` — must end with `PREFLIGHT CLEAN`. This one calls the **live** hosted mock servers and asserts every tool the examples grant actually exists there, so it doubles as proof that your network can reach the mocks (and it warns you if `requests` is missing).
- [ ] **Open this repo in Claude Code and type `/`** — confirm **`new-agent`** appears in the skill list. It ships *inside* this repo (`.claude/skills/new-agent/`, real files) and Claude Code discovers it automatically: **there is nothing to install and you do not need a zip.** (Want `/new-agent` in your *other* repos too? `cp -R .claude/skills/new-agent ~/.claude/skills/` — that's it.)
- [ ] Confirm **outcomes** and **multiagent** are enabled on your org (separate from the managed-agents beta — ask your Anthropic contact). Labs 3+ depend on these.

## Recommended

- [ ] **Claude Code** installed: `npm i -g @anthropic-ai/claude-code` — opening this repo in CC loads `CLAUDE.md` and makes your session CMA-aware
- [ ] Run `/claude-api managed-agents-onboard` in Claude Code once before the workshop — it scaffolds a hello-world agent in your language and walks the 4-resource model. Takes ~5 minutes; we'll skip it on the day if you've done it.
  - **Heads-up, and it's deliberate that we still recommend it:** the agent that flow produces is only as locked-down as the answers you give it. We ran it twice the same night: driven carefully, it gated the one write behind human approval; driven with the defaults, it enabled the **full built-in toolset and a blanket, un-allowlisted grant on every MCP server** — which, because MCP toolsets are allow-by-default, silently included every live WRITE tool. Neither run validated a single tool name against the live server. That variance — the safety living in the *interviewee's head* instead of in the config — is the first thing this workshop fixes (gotcha #4, `validate.py`, and every example in `examples/`). If you notice it yourself before the day, you've already learned the most important thing in it.

## What to bring (optional, for the "swap in your own MCP" segment)

- The URL of any **streamable-HTTP MCP server** you already have (policy admin, claims, rating, CRM)
- Or nothing — the examples ship with hosted mocks that work out of the box

## If something's blocked

Reply-all to the calendar invite with the error output and we'll sort it before the day.
