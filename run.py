#!/usr/bin/env python3
"""Run a session against a deployed Claude Managed Agent and stream the events.

Usage:
  python run.py --agent agt_... [--env env_...] [--memory-store memstore_...] "your instruction"

If --env is omitted, a default cloud environment is created and its ID printed
so you can reuse it on subsequent runs.

This is the minimal client every CMA integration needs: create a session,
open the SSE stream, send a user.message, read events until idle. Compare
the code below to the deploy recipe in CLAUDE.md — same 6 steps.
"""
import argparse
import json
import os
import sys
import threading
import requests

API = "https://api.anthropic.com"
HDRS = {
    "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "managed-agents-2026-04-01",
    "content-type": "application/json",
}


def cma(method, path, body=None, **kw):
    r = requests.request(method, f"{API}{path}", headers=HDRS, json=body, **kw)
    if not r.ok:
        sys.exit(f"error: {method} {path} -> HTTP {r.status_code}\n{r.text}")
    return r


ap = argparse.ArgumentParser()
ap.add_argument("--agent", required=True, help="agent id from deploy.py (agt_...)")
ap.add_argument("--env", help="environment id (env_...). Created if omitted.")
ap.add_argument("--memory-store", help="memory_store id to attach read_write (Lab 2)")
ap.add_argument("prompt", help="the instruction to send as the first user.message")
args = ap.parse_args()

if not HDRS["x-api-key"]:
    sys.exit("error: ANTHROPIC_API_KEY is not set")

# ── 1. Environment (reusable — create once, pass --env on later runs) ────────
env_id = args.env
if not env_id:
    env = cma("POST", "/v1/environments", {
        "name": "workshop-default",
        "config": {"type": "cloud", "networking": {"type": "unrestricted"}},
    }).json()
    env_id = env["id"]
    print(f"created environment  {env_id}   (reuse with --env {env_id})")

# ── 2. Session — memory stores attach HERE via resources[], not on the agent ─
session_body = {"agent": args.agent, "environment_id": env_id}
if args.memory_store:
    session_body["resources"] = [{
        "type": "memory_store",
        "memory_store_id": args.memory_store,
        "access": "read_write",
        "instructions": (
            "BEFORE you do anything else, list and read every file under lessons/. "
            "Before going idle, reflect: what would a FUTURE agent want to know? "
            "Already covered → write nothing. Nuance → EDIT that file. New topic "
            "only when it fits no existing one. Under ~10 files. No PII."
        ),
    }]
sess = cma("POST", "/v1/sessions", session_body).json()
sid = sess["id"]
print(f"session  {sid}")
print(f"console  https://platform.claude.com/workspaces/default/sessions/{sid}\n")


# ── 3. Open the SSE stream BEFORE posting the first event (gotcha #1) ────────
#     The POST happens from a background thread once the stream is open.
def send_first_message():
    cma("POST", f"/v1/sessions/{sid}/events", {
        "events": [{
            "type": "user.message",
            # content MUST be an array of blocks, not a bare string (gotcha #3)
            "content": [{"type": "text", "text": args.prompt}],
        }],
    })


# Workshop simplification: 0.5s is enough on a local network. Production
# clients should not sleep — open the stream, read until you see
# `session.ready` (or first heartbeat), THEN POST. See /claude-api skill
# for the lossless-reconnect pattern using `processed_at`.
threading.Timer(0.5, send_first_message).start()

with cma("GET", f"/v1/sessions/{sid}/events/stream", stream=True) as stream:
    for line in stream.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        ev = json.loads(line[5:].strip())
        et = ev.get("type", "")

        if et == "agent.text":
            print(ev.get("text", ""), end="", flush=True)
        elif et == "agent.tool_use":
            print(f"\n  → {ev.get('name')}  {json.dumps(ev.get('input', {}))[:120]}")
        elif et == "agent.tool_result":
            print(f"  ← ({len(str(ev.get('content','')))} chars)")
        elif et == "session.requires_action":
            # Lab 4 (add-vehicle) parks here on endorse_policy. Approve in Console,
            # or POST a user.tool_approval event — see add-vehicle.yaml footer.
            print(f"\n\n⏸  requires_action: {json.dumps(ev.get('action', ev), indent=2)}")
            print("    Approve in Console or POST user.tool_approval to continue.")
            break
        elif et == "session.status_idle":
            print("\n\n✅ idle — outputs (if any) at /mnt/session/outputs/ in Console")
            break
        elif et.startswith("session.error"):
            print(f"\n\n❌ {et}: {ev}")
            break
