#!/usr/bin/env python3
"""Opt-in wire-level compatibility check. Python stdlib only; no paid model calls."""
import argparse
import http.server
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

REPO = Path(__file__).resolve().parent.parent
MARKERS = ("STRUCTURED_GUIDANCE_MARKER", "APPENDED_GUIDANCE_MARKER", "Your working conversation is mirrored at")


def instructions(payload):
    parts = [payload.get("instructions") or ""]
    for message in payload.get("input", []):
        if message.get("role") in ("system", "developer"):
            content = message.get("content", "")
            parts.extend([content] if isinstance(content, str) else [block.get("text", "") for block in content])
    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pi", default="pi", help="Pi executable; use node_modules/.bin/pi for the pinned runtime")
    parser.add_argument("--extension", action="append", default=[], help="Additional extension entry point (repeatable)")
    parser.add_argument("--without-clm", action="store_true", help="Run a native-Pi baseline without this checkout")
    parser.add_argument("--require-guidance", action="append", default=[], help="Additional expected instruction marker (repeatable)")
    args = parser.parse_args()
    markers = (*(MARKERS[:2] if args.without_clm else MARKERS), *args.require_guidance)
    captures = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_POST(self):
            try:
                case = self.path.split("/")[1]
                length = int(self.headers.get("Content-Length", "0"))
                if case not in captures or length < 0:
                    raise ValueError("Unknown fixture request")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Expected a request object")
            except (ValueError, IndexError):
                self.send_error(400, "Invalid fixture request")
                return
            captures[case].append(payload)
            number = len(captures[case])
            item_id = "msg_fixture_" + case + "_" + str(number)
            part = {"type": "output_text", "text": "capture ok", "annotations": []}
            item = {"id": item_id, "type": "message", "role": "assistant", "status": "completed", "content": [part]}
            response = {"id": "resp_" + item_id, "object": "response", "status": "completed", "model": "fixture", "output": [item],
                        "usage": {"input_tokens": 100, "output_tokens": 2, "total_tokens": 102,
                                  "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}
            events = [
                {"type": "response.created", "response": {**response, "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": {**item, "status": "in_progress", "content": []}},
                {"type": "response.content_part.added", "item_id": item_id, "output_index": 0, "content_index": 0, "part": {**part, "text": ""}},
                {"type": "response.output_text.delta", "item_id": item_id, "output_index": 0, "content_index": 0, "delta": "capture ok"},
                {"type": "response.output_text.done", "item_id": item_id, "output_index": 0, "content_index": 0, "text": "capture ok"},
                {"type": "response.content_part.done", "item_id": item_id, "output_index": 0, "content_index": 0, "part": part},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": response},
            ]
            body = "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n" for event in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="pi-clm-compat-") as temporary:
            root = Path(temporary)
            seed = root / "seed.ts"
            seed.write_text('''export default function(pi) {
  pi.on("session_start", () => pi.appendEntry("add-dir:state", { dirs: [{
    absolutePath: process.env.COMPAT_EXTERNAL_DIR, label: "fixture-external", addedAt: 1,
  }] }));
}
''')
            fixture = root / "injector.ts"
            fixture.write_text('''export default function(pi) {
  pi.on("before_agent_start", event => {
    const text = "STRUCTURED_GUIDANCE_MARKER: retain fixture guidance.";
    if (event.systemPromptOptions?.sections) {
      event.systemPromptOptions.sections.compat_fixture = text;
      event.systemPromptOptions.appendSystemPrompt += "\\nAPPENDED_GUIDANCE_MARKER: retain appended guidance.";
      return;
    }
    return { systemPrompt: event.systemPrompt + "\\n" + text + "\\nAPPENDED_GUIDANCE_MARKER: retain appended guidance." };
  });
}
''')
            paths = {"injector": fixture} if args.without_clm else {"clm": REPO / "index.ts", "injector": fixture}
            paths.update({"extension-" + str(i): Path(path).resolve() for i, path in enumerate(args.extension)})
            pi = str(Path(args.pi).resolve()) if Path(args.pi).is_file() else args.pi
            failures = []
            for number, order in enumerate(itertools.permutations(paths), 1):
                case = str(number)
                captures[case] = []
                directory = root / case
                agent, workspace, external = [directory / name for name in ("agent", "workspace", "external")]
                for path in (agent, workspace, external):
                    path.mkdir(parents=True)
                (external / "AGENTS.md").write_text("EXTERNAL_GUIDANCE_MARKER: fixture directory instructions.\n")
                (agent / "settings.json").write_text(json.dumps({"compaction": {"enabled": False}, "retry": {"enabled": False}, "cacheWarming": "off"}))
                (agent / "models.json").write_text(json.dumps({"providers": {"capture-fixture": {
                    "baseUrl": "http://127.0.0.1:%d/%s/v1" % (server.server_address[1], case),
                    "api": "openai-responses", "apiKey": "local-fixture", "models": [{"id": "fixture", "name": "Offline fixture",
                    "reasoning": False, "input": ["text"], "contextWindow": 100000, "maxTokens": 128,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]}}}))
                env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR", "COMSPEC") if key in os.environ}
                env.update({"HOME": str(agent), "PI_CODING_AGENT_DIR": str(agent), "PI_OFFLINE": "1", "PI_SKIP_VERSION_CHECK": "1",
                            "PI_TELEMETRY": "0", "NO_PROXY": "127.0.0.1,localhost", "COMPAT_EXTERNAL_DIR": str(external)})
                command = [pi, "--offline", "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes", "--no-context-files",
                           "--no-session", "--model", "capture-fixture/fixture", "--thinking", "off", "-e", str(seed)]
                for name in order:
                    command += ["-e", str(paths[name])]
                command += ["--print", "Fixture first turn.", "Fixture second turn.", "Fixture third turn."]
                try:
                    if number == 1:
                        version = subprocess.run([pi, "--version"], cwd=workspace, env=env, stdin=subprocess.DEVNULL,
                                                 capture_output=True, text=True, timeout=10)
                        if version.returncode:
                            raise RuntimeError("Cannot identify Pi runtime: " + version.stderr[-1000:])
                        print("Pi runtime: " + version.stdout.strip() + " (" + pi + ")", flush=True)
                    result = subprocess.run(command, cwd=workspace, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=40)
                    if result.returncode:
                        raise RuntimeError("Pi failed: " + result.stderr[-1000:])
                    payloads = captures[case]
                    if len(payloads) != 3:
                        raise RuntimeError("Expected three completed requests; captured " + str(len(payloads)))
                    for index, payload in enumerate(payloads, 1):
                        missing = [marker for marker in markers if instructions(payload).count(marker) != 1]
                        if missing:
                            raise RuntimeError("Request %d: missing or duplicated %s" % (index, ", ".join(missing)))
                        tools = {tool.get("name") for tool in payload.get("tools", [])}
                        if not args.without_clm and not {"live_context_annotate", "live_context_recall"}.issubset(tools):
                            raise RuntimeError("CLM tools were not declared")
                    print("PASS: " + " -> ".join(order), flush=True)
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                    failures.append(" -> ".join(order))
                    print("FAIL: " + failures[-1] + ": " + str(error), flush=True)
            if failures:
                raise SystemExit(1)
            print("All %d orders / %d final HTTP requests preserve the required guidance." % (len(captures), sum(map(len, captures.values()))))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
