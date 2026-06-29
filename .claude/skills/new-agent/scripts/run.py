#!/usr/bin/env python3
"""Run a session against a deployed Claude Managed Agent and stream the events.

Usage:
  python3 run.py --agent agent_... [--env env_...] [--memory-store memstore_...] "your instruction"
  python3 run.py --ui --agent agent_... "your instruction"        # + a local browser view

If --env is omitted, a default cloud environment is created and its ID printed
so you can reuse it on subsequent runs.

This is the minimal client every CMA integration needs: create a session,
open the SSE stream, send a user.message, read events until idle. Compare
the code below to the deploy recipe in CLAUDE.md — same 6 steps.

--ui additionally serves a small localhost-only page (stdlib http.server —
no new dependency) that mirrors the SAME run and turns the requires_action
[y/n] terminal prompt into an Approve / Deny card a non-engineer can use.
The ANTHROPIC_API_KEY never reaches the browser: the server is bound to
127.0.0.1, the page only ever talks back to 127.0.0.1, and every Anthropic
API call is still made from this process. Without --ui nothing changes.
"""
import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # --ui only (stdlib)
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
ap.add_argument("--agent", required=True, help="agent id from deploy.py (agent_...)")
ap.add_argument("--env", help="environment id (env_...). Created if omitted.")
ap.add_argument("--memory-store", help="memory_store id to attach read_write — the workflow's own learnings")
ap.add_argument("--readonly-store", help="memory_store id to attach read_only — the claims manual / SOPs / reference standards. The agent reads it; it can NEVER write to it.")
ap.add_argument("--rubric", help="path to an outcomes rubric (markdown). The run becomes a GRADED run: the kickoff is sent as a single user.define_outcome event carrying BOTH your instruction and this rubric, and after the agent goes idle a grader scores /mnt/session/outputs/** against it and emits an outcome.result event, which this script prints.")
ap.add_argument("--ui", action="store_true",
                help="also serve a localhost browser view of this run (127.0.0.1 only) and take "
                     "the requires_action Approve / Deny from that page instead of the terminal")
ap.add_argument("prompt", help="the instruction to send as the first user.message")
args = ap.parse_args()

if not HDRS["x-api-key"]:
    sys.exit("error: ANTHROPIC_API_KEY is not set")
if args.rubric and not os.path.isfile(args.rubric):
    sys.exit(f"error: --rubric file not found: {args.rubric}")


# ── --ui : a localhost browser view of the SAME run ──────────────────────────
# Reading this file for the 6-step CMA flow? Skip ahead to "1. Environment" —
# nothing in this block runs unless --ui is passed, and that flow is unchanged.
#
# What --ui adds: a stdlib ThreadingHTTPServer bound to 127.0.0.1 on a free
# port, started as a DAEMON thread before the SSE stream opens. It serves
# ui.html (GET /), a JSON snapshot of this run (GET /state, polled ~700ms by
# the page), and takes the human's decision (POST /approve). The SSE loop
# below stays on the main thread and remains the ONLY thing that talks to the
# Anthropic API: the key is never put in /state and never sent to the page,
# and the page only ever talks back to 127.0.0.1.
#
# The requires_action handoff — the whole point of the page:
#
#   main thread (the SSE loop)                  HTTP handler thread
#   ──────────────────────────                  ───────────────────────────
#   ui_await_decision(pending):
#     lock: publish pending,
#           status=requires_action,
#           decision=None, event.clear()
#     loop: event.wait(0.5)      ──────────▶    POST /approve arrives:
#       (0.5 s slices, forever, so a              lock: pending still set?
#        Ctrl-C lands between waits                     not already answered?
#        instead of being swallowed                     deposit the decision
#        by one long native wait)                       event.set()
#     event is set   ◀──────────────────────    reply {"ok": true}
#     lock: take the decision,
#           pending=None, status=running
#     return it → the caller builds the SAME user.tool_confirmation body the
#     terminal path builds, POSTs it, and keeps reading the SAME stream.
#
#   The decision is written BEFORE event.set(), both under UI["lock"], and the
#   waiter re-acquires that same lock after waking — so it can never observe
#   the Event set without the decision being there. A duplicate /approve gets
#   a 409 from the two guards. Nothing in this block ever calls input(), and
#   nothing in it ever sees the API key.

UI = None        # stays None without --ui → every ui_* helper below is a no-op
FEED_MAX = 500   # the page's feed is a bounded window, not an unbounded log


def ui_feed(kind, **fields):
    """Append one entry to the page's feed (no-op unless --ui is live).

    Consecutive agent.text chunks coalesce into one entry so the page shows
    paragraphs, not one row per streamed token; FEED_MAX bounds the list.
    """
    if UI is None:
        return
    with UI["lock"]:
        feed = UI["state"]["feed"]
        if kind == "text" and feed and feed[-1]["kind"] == "text":
            feed[-1]["text"] += fields.get("text", "")
        else:
            feed.append({"kind": kind, **fields})
            if len(feed) > FEED_MAX:
                del feed[: len(feed) - FEED_MAX]
        UI["state"]["rev"] += 1


def ui_set(**fields):
    """Update top-level page state (status, …). No-op unless --ui is live."""
    if UI is None:
        return
    with UI["lock"]:
        UI["state"].update(fields)
        UI["state"]["rev"] += 1


def ui_await_decision(pending):
    """Park the SSE (main) thread until the page POSTs /approve, then return
    the {"decision": "approve"|"deny", "reason"?: str} dict it deposited.

    The wait is an unbounded loop of SHORT Event.wait(0.5) slices: between
    slices the interpreter is back in Python bytecode, so Ctrl-C is raised
    here instead of being stuck inside one long native wait. There is no
    deadline — a human gate waits as long as the human does.
    """
    with UI["lock"]:
        UI["decision"] = None
        UI["decision_ready"].clear()
        UI["state"]["pending"] = pending
        UI["state"]["status"] = "requires_action"
        UI["state"]["rev"] += 1
    print(f"\n    ⏸  waiting for Approve / Deny in the browser →  {UI['url']}")
    while not UI["decision_ready"].wait(timeout=0.5):
        pass  # no answer yet; loop so KeyboardInterrupt can land between waits
    with UI["lock"]:
        decision = UI["decision"]
        UI["decision"] = None
        UI["state"]["pending"] = None
        UI["state"]["status"] = "running"
        UI["state"]["rev"] += 1
    return decision


class _UIServer(ThreadingHTTPServer):
    daemon_threads = True  # an open keep-alive connection must never block exit

    def handle_error(self, request, client_address):
        # A tab closing mid-response raises in its handler thread. Never let
        # socketserver print that traceback across the live agent transcript.
        pass


class _UIHandler(BaseHTTPRequestHandler):
    """GET / → ui.html · GET /state → JSON snapshot · POST /approve → decision.

    Locked down to the page we served:
      * bound to 127.0.0.1 only (see ui_start);
      * the Host header must be exactly ours  → kills DNS-rebinding;
      * Origin / Sec-Fetch-Site (when the browser sends them) must be
        same-origin on /state and /approve → kills cross-site reads/POSTs;
      * no Access-Control-Allow-Origin is ever emitted.
    Responses never contain the API key: /state is built only from
    UI["state"] (ids, console URL, status, feed, pending).
    """

    protocol_version = "HTTP/1.1"   # keep-alive; _send always sets Content-Length
    server_version = "run-py-ui"    # don't advertise the Python version
    sys_version = ""

    def log_message(self, *_):      # the 700 ms /state poll must not spam stdout
        pass

    # -- plumbing -------------------------------------------------------------
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj).encode("utf-8"))

    def _host_ok(self):
        return (self.headers.get("Host") or "").strip().lower() in UI["hosts"]

    def _same_origin(self):
        if not self._host_ok():
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin.lower() not in UI["origins"]:
            return False
        sfs = self.headers.get("Sec-Fetch-Site")
        return sfs is None or sfs in ("same-origin", "none")

    # -- routes ---------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            # A top-level navigation may legitimately come from a pasted link,
            # so only the Host pin applies here; the data routes below get the
            # full same-origin check.
            if not self._host_ok():
                return self._json(403, {"error": "forbidden"})
            return self._send(200, "text/html; charset=utf-8", UI["html"])
        if not self._same_origin():
            return self._json(403, {"error": "same-origin only"})
        if path == "/state":
            with UI["lock"]:
                body = json.dumps(UI["state"]).encode("utf-8")
            return self._send(200, "application/json; charset=utf-8", body)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._same_origin():
            return self._json(403, {"error": "same-origin only"})
        if self.path.split("?", 1)[0] != "/approve":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 <= n <= 65536:
            self.close_connection = True
            return self._json(413, {"error": "request body too large"})
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(req, dict):
                raise ValueError("not an object")
        except ValueError:
            return self._json(400, {"error": "body must be a JSON object"})
        decision = req.get("decision")
        if decision not in ("approve", "deny"):
            return self._json(400, {"error": 'decision must be "approve" or "deny"'})
        # Hand off to the SSE thread parked in ui_await_decision(). This
        # thread never touches the Anthropic API — it deposits the decision and
        # signals; the main thread builds and POSTs the user.tool_confirmation.
        with UI["lock"]:
            if UI["state"]["pending"] is None:
                return self._json(409, {"error": "nothing is waiting for approval"})
            if UI["decision"] is not None:
                return self._json(409, {"error": "already answered"})
            UI["decision"] = {"decision": decision}
            if decision == "deny" and str(req.get("reason") or "").strip():
                UI["decision"]["reason"] = str(req["reason"]).strip()[:2000]
            UI["decision_ready"].set()   # set strictly AFTER the deposit, same lock
        return self._json(200, {"ok": True, "decision": decision})


def ui_start(session_id, console_url):
    """Read ui.html (next to this file), bind 127.0.0.1 on an OS-chosen free
    port, and serve it from a daemon thread. Returns the URL — or None after
    printing one line, in which case UI stays None and everything falls back
    to the plain terminal prompt instead of crashing."""
    global UI
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.html")
    try:
        with open(html_path, "rb") as f:
            html = f.read()
    except OSError:
        print(f"error: --ui needs {html_path} and it could not be read — "
              "continuing WITHOUT the browser view (terminal [y/n] prompt).")
        return None
    try:
        srv = _UIServer(("127.0.0.1", 0), _UIHandler)  # loopback ONLY; port 0 = pick a free one
    except OSError as e:
        print(f"error: --ui could not bind a port on 127.0.0.1 ({e}) — "
              "continuing WITHOUT the browser view (terminal [y/n] prompt).")
        return None
    port = srv.server_address[1]
    UI = {
        "lock": threading.Lock(),
        "decision": None,                   # written by POST /approve, under `lock`
        "decision_ready": threading.Event(),
        "html": html,
        "url": f"http://127.0.0.1:{port}",
        "hosts": {f"127.0.0.1:{port}", f"localhost:{port}"},
        "origins": {f"http://127.0.0.1:{port}", f"http://localhost:{port}"},
        # Everything the browser is allowed to see. The API key is NOT here.
        "state": {
            "rev": 0,
            "agent": args.agent,
            "session": session_id,
            "console": console_url,
            "status": "running",  # running | requires_action | idle | error
            "feed": [],           # [{kind: text|tool_use|tool_result|approval_request|decision|status|error, …}]
            "pending": None,      # {tool_use_id, name, input} while parked at requires_action
        },
    }
    threading.Thread(target=srv.serve_forever, daemon=True, name="ui-http").start()
    return UI["url"]
# ─────────────────────────────────────────────────── end of the --ui block ───


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
# The two flags model the two memory ROLES (docs/memory-best-practices.md):
#   --readonly-store : the MANUAL — SOPs / standards the org wrote. Frozen.
#   --memory-store   : the LEARNINGS — what this workflow figures out. Mutable.
# Attaching both is the recommended architecture; the contrast ("the manual" vs
# "what the agent learned") is what a compliance reviewer needs to see.
session_body = {"agent": args.agent, "environment_id": env_id}
resources = []
if args.readonly_store:
    # `read_only` is the EXACT literal. The known footgun: the typo `readonly`
    # is silently accepted and ESCALATES to read_write — a privilege-escalation
    # bug, and exactly the prompt-injection vector a shared store must not have.
    resources.append({
        "type": "memory_store",
        "memory_store_id": args.readonly_store,
        "access": "read_only",
        "instructions": (
            "Reference material: the organization's claims manual, SOPs, and "
            "standards. BEFORE acting, list and read every file here. CITE the "
            "specific file and rule behind every recommendation you ground in "
            "it. You cannot write to this store; never claim a rule exists "
            "here that you did not actually read."
        ),
    })
if args.memory_store:
    resources.append({
        "type": "memory_store",
        "memory_store_id": args.memory_store,
        "access": "read_write",
        "instructions": (
            "BEFORE you do anything else, list and read every file under lessons/. "
            "Before going idle, reflect: what would a FUTURE agent want to know? "
            "Already covered → write nothing. Nuance → EDIT that file. New topic "
            "only when it fits no existing one. Under ~10 files. No PII."
        ),
    })
if resources:
    session_body["resources"] = resources
sess = cma("POST", "/v1/sessions", session_body).json()
sid = sess["id"]
console = f"https://platform.claude.com/workspaces/default/sessions/{sid}"
print(f"session  {sid}")
print(f"console  {console}\n")

# --ui: bring the page up now, from a daemon thread, BEFORE the SSE stream
# opens (step 3) — so the browser can be watching from the very first event.
# If ui.html is missing, ui_start() says so in one line and returns None: UI
# stays None and the rest of the file behaves exactly like a run without --ui.
if args.ui:
    ui_url = ui_start(sid, console)
    if ui_url:
        print(f"UI       {ui_url}   (open this in a browser — approvals happen there)\n")


# ── 3. Open the SSE stream BEFORE posting the first event (gotcha #1) ────────
#     The POST happens from a background thread once the stream is open.
def send_first_message():
    # A plain run kicks off with a user.message. A GRADED run (--rubric) kicks off
    # with ONE user.define_outcome event INSTEAD — it carries BOTH the task (its
    # `description`) and the rubric, and tells the platform to grade the output
    # once the session goes idle. Two things people get wrong, both verified
    # against a working client: the rubric is NOT a session-create resource, and
    # it is not a bare string — it is a nested {"type": "text", "content": "..."}.
    if args.rubric:
        ev = {
            "type": "user.define_outcome",
            "description": args.prompt,
            "rubric": {"type": "text", "content": open(args.rubric).read()},
            "max_iterations": 5,
        }
    else:
        ev = {
            "type": "user.message",
            # content MUST be an array of blocks, not a bare string (gotcha #3)
            "content": [{"type": "text", "text": args.prompt}],
        }
    cma("POST", f"/v1/sessions/{sid}/events", {"events": [ev]})


# Workshop simplification: 0.5s is enough on a local network. Production
# clients should not sleep — open the stream, read until you see
# `session.ready` (or first heartbeat), THEN POST. See /claude-api skill
# for the lossless-reconnect pattern using `processed_at`.
threading.Timer(0.5, send_first_message).start()

# Tool calls waiting on a human, keyed by their event id (sevt_…). An
# agent.mcp_tool_use / agent.tool_use that arrives with `evaluated_permission`
# == "ask" goes in here; the session.status_idle whose stop_reason names those
# ids drains it (one user.tool_confirmation per id).
PENDING = {}

with cma("GET", f"/v1/sessions/{sid}/events/stream", stream=True) as stream:
    for line in stream.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        ev = json.loads(line[5:].strip())
        et = ev.get("type", "")

        if et == "agent.text":
            print(ev.get("text", ""), end="", flush=True)
            ui_feed("text", text=ev.get("text", ""))
        elif et in ("agent.tool_use", "agent.mcp_tool_use"):
            preview = json.dumps(ev.get("input", {}))[:120]
            print(f"\n  → {ev.get('name')}  {preview}")
            ui_feed("tool_use", name=ev.get("name"), preview=preview)
            if ev.get("evaluated_permission") == "ask":
                # A tool guarded by permission_policy: always_ask. NO result will
                # follow this call; the session is about to PARK (the next
                # session.status_idle carries stop_reason.type == "requires_action"
                # pointing back at THIS event's id). The event carries the FULL
                # input the human is being asked to approve. Show all of it —
                # "here is the exact change you are authorizing" IS the demo.
                # Don't truncate.
                if ev.get("id"):
                    PENDING[ev["id"]] = ev
                print(f"\n⏸  HUMAN APPROVAL REQUIRED — the agent wants to call:  {ev.get('name')}")
                print(json.dumps(ev.get("input", {}), indent=2))
                ui_feed("approval_request", name=ev.get("name"), tool_use_id=ev.get("id"))
        elif et in ("agent.tool_result", "agent.mcp_tool_result"):
            print(f"  ← ({len(str(ev.get('content','')))} chars)")
            ui_feed("tool_result", chars=len(str(ev.get("content", ""))))
        elif et == "outcome.result":
            # The grader's verdict on a --rubric run. This is the moment the
            # rubric stops being a document and becomes a score: edit the rubric,
            # re-run the same instruction, and watch this number move.
            print("\n\n📊 OUTCOME — the grader's score for this run:")
            print(json.dumps(ev.get("result", ev), indent=2)[:2000])
        elif et == "session.status_idle":
            # status_idle is NOT always the end — its stop_reason says why the
            # agent stopped:
            #   * requires_action → the session is PAUSED on the tool call(s)
            #     listed in stop_reason.event_ids: the agent.mcp_tool_use /
            #     agent.tool_use events that arrived with evaluated_permission
            #     "ask" (held in PENDING). Nothing happens until a human answers
            #     each one with a user.tool_confirmation. This is the
            #     human-in-the-loop gate that `permission_policy: always_ask`
            #     buys you: a CONFIG property, not a prompt-level hope. A real
            #     client (an adjuster UI, a supervisor's queue) renders the
            #     pending call and POSTs the answer; here that client is you and
            #     one keypress — or, with --ui, one click in the browser. After
            #     you answer, the agent resumes on THIS SAME stream: no Console,
            #     no restart, and NO break.
            #   * anything else (end_turn, retries_exhausted, …) → the run is over.
            sr = ev.get("stop_reason") or {}
            if sr.get("type") == "requires_action":
                ids = sr.get("event_ids") or []
                if not ids:
                    # The stream shape changed and there's nothing to answer.
                    # Defer to the Console rather than guess.
                    print(f"\n\n⏸  requires_action, but no event_ids on the stop_reason:\n{json.dumps(ev, indent=2)}")
                    print("    Answer it in the platform Console; still listening on this stream.")
                    ui_feed("error", text="requires_action arrived without event_ids — "
                                          "answer it in the platform Console.")
                for tu in ids:
                    req = PENDING.get(tu)
                    if req is None:
                        print(f"\n\n⏸  requires_action points at {tu}, but that tool_use event was never seen.")
                        print("    Answer it in the platform Console; still listening on this stream.")
                        ui_feed("error", text=f"requires_action points at {tu}, but that tool_use "
                                              "event was never seen — answer it in the platform Console.")
                        continue
                    name = req.get("name") or "the pending tool"
                    if UI is not None:
                        # --ui: the browser is the human. Publish the pending call
                        # (tool name + the FULL input from the "ask" tool_use
                        # event) and park this thread until the page POSTs
                        # /approve. No input() — but the event we build, and the
                        # resume, are EXACTLY the same as the terminal path's.
                        got = ui_await_decision({"tool_use_id": tu, "name": name,
                                                 "input": req.get("input") or {}})
                        allow = got["decision"] == "approve"
                        note = got.get("reason")
                    else:
                        try:
                            ans = input(f"\n    Approve {name}? [y = approve / anything else = deny]  ").strip().lower()
                        except EOFError:
                            ans = ""
                        allow = ans == "y"
                        note = None
                    confirmation = {"type": "user.tool_confirmation", "tool_use_id": tu,
                                    "result": "allow" if allow else "deny"}
                    if not allow and note:
                        confirmation["deny_message"] = note
                    cma("POST", f"/v1/sessions/{sid}/events", {"events": [confirmation]})
                    print(f"    → {'approved' if allow else 'denied'}. Resuming the stream…\n")
                    ui_feed("decision", decision="approve" if allow else "deny", name=name,
                            reason=confirmation.get("deny_message"))
                    PENDING.pop(tu, None)
                # Deliberately NO `break`: the session was only paused, and the
                # agent now resumes on this SAME stream — keep reading it.
                continue
            why = f" ({sr['type']})" if sr.get("type") else ""
            print(f"\n\n✅ idle{why} — outputs (if any) at /mnt/session/outputs/ in Console")
            ui_feed("status", text=f"idle{why} — outputs (if any) at /mnt/session/outputs/ in Console")
            ui_set(status="idle")
            break
        elif et.startswith("session.error"):
            print(f"\n\n❌ {et}: {ev}")
            ui_feed("error", text=f"{et}: {json.dumps(ev)}")
            ui_set(status="error")
            break

# --ui: the page polls /state every ~700 ms. Give it a beat to pick up the
# final status (idle / error) before this process — and with it the daemon
# HTTP thread — exits and the page goes read-only ("disconnected").
if UI is not None:
    time.sleep(2.0)
