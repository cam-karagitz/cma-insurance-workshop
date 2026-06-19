# Claude Managed Agents — Workshop Kit

You are helping build **Claude Managed Agents (CMA)**: Anthropic-hosted agents that run in cloud sandboxes. All calls require header `anthropic-beta: managed-agents-2026-04-01`.

## The 4-resource model

| Resource | What it is | Create via |
|---|---|---|
| **Agent** | Versioned config: `{name, model, system, tools[], mcp_servers?, multiagent?, metadata?}` | `POST /v1/agents` |
| **Environment** | Container template: `{name, config:{type:"cloud", networking, packages?}}` | `POST /v1/environments` |
| **Session** | Running instance: `{agent:<id>, environment_id:<id>, resources?[]}` | `POST /v1/sessions` |
| **Events** | The wire: `user.*` / `agent.*` / `session.*` over SSE | `GET …/events/stream` + `POST …/events` |

## Agent config shape

The YAML files in `examples/` map **1:1** to the `POST /v1/agents` JSON body. Minimal:

```yaml
name: my-agent
model: claude-opus-4-8
system: |
  <prompt — keep long prompts in prompts/*.md and read them in deploy.py>
tools:
  - type: agent_toolset_20260401          # built-in sandbox tools
    default_config: { enabled: false }    # deny-by-default, then allowlist:
    configs: [{name: read, enabled: true}, {name: grep, enabled: true}]
  - type: mcp_toolset
    mcp_server_name: claims-admin
    default_config: { enabled: true, permission_policy: {type: always_allow} }  # see gotcha #2
    configs: [{name: file_fnol, enabled: false}]   # blocklist write tools
mcp_servers:
  - { type: url, name: claims-admin, url: https://YOUR-DOMAIN/mcp }
multiagent:                               # orchestrators only — sub-agents must exist first
  type: coordinator
  agents: [{type: agent, id: agt_..., version: 1}]
metadata: { owner: <you>, workflow: <name>, role: Orchestrator|Reader|Writer }  # free-form; convention only
```

## Deploy recipe (what `deploy.py` does)

1. `POST /v1/agents` for each sub-agent → capture `{id, version}`
2. `POST /v1/agents` for the orchestrator with `multiagent.agents` populated from step 1
3. `POST /v1/environments` → capture `environment_id`
4. `POST /v1/sessions {agent, environment_id}`
5. **Open** `GET /v1/sessions/:id/events/stream` (SSE)
6. **Then** `POST /v1/sessions/:id/events {events:[{type:"user.message", content:[{type:"text", text:"…"}]}]}`
7. Verify: `GET /v1/agents/:id` and confirm `multiagent` is populated (API silently drops unknown fields)

## Top gotchas

1. **Open the SSE stream BEFORE posting the first event.** Session-create only provisions the container; nothing runs until an event arrives, and POST-before-stream means you miss early `agent.*` events. This is the #1 failure mode.
2. **MCP toolsets default to `permission_policy: always_ask`** (built-in `agent_toolset` defaults to `always_allow`). Forget to override and the session stalls at `stop_reason: requires_action`. Fix: set `default_config.permission_policy: {type: always_allow}` on every `mcp_toolset`.
3. **`user.message.content` must be an array of content blocks**, not a bare string. Also: agent updates require `{"version": N, …}` in the body (optimistic concurrency); the roster field is `multiagent` — older `callable_agents` is silently ignored.

## Architecture convention — 3-tier least-privilege

- **Orchestrator**: Read/Grep only. Delegates; never writes, never holds Bash.
- **Reader** sub-agents: Read + read-only MCP tools. No Write. Parse untrusted inputs here.
- **Writer** sub-agent (exactly one): Write/Edit/Bash. No MCP. All production output goes through it.
- System prompts enforce: *agent recommends, doesn't decide* — outputs are drafts for human sign-off.

## When the user asks to build an agent

1. **Match the user's ask to a pillar (claims / service / sales) first, then the closest example.** Copy it; don't write configs from scratch.
   - `claims/fnol-triage.yaml` — teaches: single agent, one MCP, deny-by-default toolset (simplest possible)
   - `claims/adjudication.yaml` — teaches: 3-tier multi-agent orchestration (reader / worker / writer) — the capstone
   - `service/coverage-explainer.yaml` — teaches: memory store attached at session-create via `resources[]`
   - `service/add-vehicle.yaml` — teaches: human-in-the-loop write — `always_ask` → handle `requires_action`
   - `sales/quote-builder.yaml` — teaches: multiple MCP servers with per-tool blocklists
   - `sales/renewal-retention.yaml` — teaches: outcomes rubric — agent self-grades its own output
2. Edit the YAML; keep tool grants minimal per the 3-tier pattern above.
3. Set `metadata.owner` / `workflow` / `role` — shared orgs fill fast and unlabeled agents get lost.
4. `python deploy.py <file.yaml>` — creates the agent, prints `agt_...`. Then `python run.py --agent agt_... "<instruction>"` — creates a session, opens SSE, streams events. **deploy.py defines, run.py invokes.** In production, run.py becomes a webhook handler / cron / UI action.
5. Memory stores attach at **session-create** via `resources[]`, not on the agent — `run.py --memory-store memstore_...` does this; see `service/coverage-explainer.yaml` footer and `docs/memory-best-practices.md`.

## Going deeper

For API details beyond this kit (memory stores, vaults, outcomes, dreaming, streaming reconnect, SDK code generation), invoke the **`claude-api` skill** — e.g. `/claude-api managed-agents-onboard` scaffolds the session create + SSE loop in the project's language. The skill teaches the client mechanics; this kit provides the domain-shaped configs on top.
