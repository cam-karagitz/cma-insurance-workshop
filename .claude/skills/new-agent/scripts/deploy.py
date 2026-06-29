#!/usr/bin/env python3
"""Deploy a Claude Managed Agent from a YAML config.

Usage:  ANTHROPIC_API_KEY=sk-ant-... python3 deploy.py [--dry-run] agent.yaml

The YAML file defines an agent and (optionally) an environment to create
alongside it. See examples/ for the schema. With --dry-run, prints the
exact JSON request bodies that WOULD be sent (no API calls, no key needed).
"""
import json
import os
import sys
import yaml

API = "https://api.anthropic.com"
BETA = "managed-agents-2026-04-01"


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def cma(method: str, path: str, body: dict | None = None) -> dict:
    import requests  # lazy — so --dry-run works without it installed
    resp = requests.request(
        method, f"{API}{path}",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": BETA,
            "content-type": "application/json",
        },
        json=body,
    )
    if not resp.ok:
        fail(f"{method} {path} -> HTTP {resp.status_code}\n{resp.text}")
    return resp.json()


argv = sys.argv[1:]
DRY_RUN = "--dry-run" in argv
argv = [a for a in argv if a != "--dry-run"]
if len(argv) != 1:
    fail("usage: python3 deploy.py [--dry-run] <agent.yaml>")

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY and not DRY_RUN:
    fail("ANTHROPIC_API_KEY is not set in the environment")

with open(argv[0]) as f:
    docs = [d for d in yaml.safe_load_all(f) if d]

if DRY_RUN:
    _n = 0
    def cma(method, path, body=None):  # noqa: F811
        global _n; _n += 1
        print(f"\n--- {method} {API}{path} ---")
        print(json.dumps(body, indent=2))
        return {"id": f"agt_DRYRUN_{_n}", "version": 1}

AGENT_FIELDS = ("name", "model", "system", "description", "tools",
                "mcp_servers", "skills", "multiagent", "metadata")

env_id = None
created: dict[str, tuple[str, int]] = {}  # name -> (id, version)

# Multi-doc files: deploy sub-agents (no `multiagent`) first, coordinators last.
# In a coordinator's roster, an `id` that matches a sibling doc's `name` is
# resolved to that agent's real id+version — so the YAML stays self-contained.
for cfg in sorted(docs, key=lambda d: "multiagent" in d):
    # environment block can ride on any doc (typically the first)
    if cfg.get("environment_id"):
        env_id = cfg["environment_id"]
    if "environment" in cfg:
        env = cma("POST", "/v1/environments", cfg["environment"])
        env_id = env["id"]
        print(f"created environment  {env_id}")

    spec = {k: cfg[k] for k in AGENT_FIELDS if k in cfg}
    for entry in spec.get("multiagent", {}).get("agents", []):
        if entry.get("id") in created:
            entry["id"], entry["version"] = created[entry["id"]]

    agent = cma("POST", "/v1/agents", spec)
    created[spec["name"]] = (agent["id"], agent["version"])
    role = "coordinator" if "multiagent" in spec else "agent      "
    print(f"created {role}  {agent['id']}  v{agent['version']}  {spec['name']}")

print()
print(f"Console: https://platform.claude.com/workspaces/default/agents/{agent['id']}")
print()
if env_id:
    print("Next: create a session with")
    print(f'  POST /v1/sessions  {{"agent": "{agent["id"]}", "environment_id": "{env_id}"}}')
else:
    print("Next: create an environment, then a session:")
    print('  POST /v1/environments  {"name": "...", "config": {"type": "cloud", "networking": {"type": "unrestricted"}}}')
    print(f'  POST /v1/sessions      {{"agent": "{agent["id"]}", "environment_id": "<env_id>"}}')
print("then open the SSE stream BEFORE posting your first user.message event.")
