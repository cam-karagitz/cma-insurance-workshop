#!/usr/bin/env python3
"""Deploy a Claude Managed Agent from a YAML config.

Usage:  ANTHROPIC_API_KEY=sk-ant-... python deploy.py agent.yaml

The YAML file defines an agent and (optionally) an environment to create
alongside it. See examples/ for the schema.
"""
import os
import sys
import requests
import yaml

API = "https://api.anthropic.com"
BETA = "managed-agents-2026-04-01"


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def cma(method: str, path: str, body: dict | None = None) -> dict:
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


if len(sys.argv) != 2:
    fail("usage: python deploy.py <agent.yaml>")

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    fail("ANTHROPIC_API_KEY is not set in the environment")

with open(sys.argv[1]) as f:
    cfg = yaml.safe_load(f)

# 1. Environment — create one if an inline `environment:` block is given,
#    otherwise use the provided `environment_id`.
env_id = cfg.get("environment_id")
if "environment" in cfg:
    env = cma("POST", "/v1/environments", cfg["environment"])
    env_id = env["id"]
    print(f"created environment  {env_id}")
elif not env_id:
    fail("config must set either `environment_id` or an `environment:` block")

# 2. Agent — build the spec from the YAML. `metadata` is free-form key/value;
#    stash whatever your own tooling needs (owner, workflow, role, category, …).
spec = {
    "name": cfg["name"],
    "model": cfg["model"],
    "system": cfg["system"],
    "metadata": cfg.get("metadata", {}),
}
if "description" in cfg:
    spec["description"] = cfg["description"]
if "tools" in cfg:
    spec["tools"] = cfg["tools"]
if "mcp_servers" in cfg:
    spec["mcp_servers"] = cfg["mcp_servers"]

agent = cma("POST", "/v1/agents", spec)
print(f"created agent        {agent['id']}  (version {agent['version']})")
print()
print(f"Console: https://platform.claude.com/workspaces/default/agents/{agent['id']}")
print()
print("Next: create a session with")
print(f'  POST /v1/sessions  {{"agent": "{agent["id"]}", "environment_id": "{env_id}"}}')
print("then open the SSE stream BEFORE posting your first user.message event.")
