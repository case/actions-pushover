"""Tests send.sh and action.yml. Run with bin/test."""

import http.server
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from curl_call import load_args, problems

REPO = Path(__file__).resolve().parent.parent
STUB_DIR = REPO / "test" / "stub"
SEND = REPO / "send.sh"
# Above curl's own --max-time 30 in send.sh, so a harness kill never masks curl's timeout.
TIMEOUT = 60

INPUTS = {
    "PUSHOVER_API_TOKEN": "t",
    "PUSHOVER_USER_KEY": "u",
    "PUSHOVER_TITLE": "x",
    "PUSHOVER_MESSAGE": "y",
}


def real_curl() -> str:
    # Resolved without test/stub on PATH, so the stub can never forward to itself.
    path = os.pathsep.join(
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if Path(p).resolve() != STUB_DIR
    )
    curl = shutil.which("curl", path=path)
    if curl is None:
        raise RuntimeError("curl not found on PATH")
    return curl


def run_send(
    curl_args: Path, inputs: dict[str, str], **extra: str
) -> subprocess.CompletedProcess[str]:
    """Runs send.sh with the stub curl first on PATH and only the given inputs set."""
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("CURL_", "PUSHOVER_"))
    }
    env.update(inputs, **extra)
    env["PATH"] = f"{STUB_DIR}{os.pathsep}{os.environ.get('PATH', '')}"
    env["CURL_ARGS"] = str(curl_args)
    return subprocess.run(
        [str(SEND)],
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )


@contextmanager
def fake_pushover(status: int) -> Generator[str, None, None]:
    """Serves POSTs on a loopback port with the given status and yields the URL."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if status == 200:
                body = {"status": 1, "request": "fake"}
            else:
                body = {
                    "status": 0,
                    "errors": [f"fake error {status}"],
                    "request": "fake",
                }
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class ActionTest(unittest.TestCase):
    def test_action_yml_has_no_expression_in_run(self) -> None:
        # An expression in run: is spliced into the script text before bash parses it.
        lines = (REPO / "action.yml").read_text(encoding="utf-8").splitlines()
        starts = [i for i, line in enumerate(lines) if re.match(r"\s*run:", line)]
        self.assertTrue(starts, "action.yml has no run: line")
        after_run = lines[starts[0] :]
        self.assertFalse(
            any("${{" in line for line in after_run),
            "action.yml has a ${{ }} expression inside a run: block",
        )


class SendTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)

    def test_hostile_inputs_reach_curl_literally(self) -> None:
        canary = self.scratch / "pwned"
        title = f"it's \"quoted\" $HOME `touch {canary}` $(touch {canary}) '; touch {canary}; '"
        message = "line one\nline two & title=evil @/etc/passwd <x> \\ ünï"
        record = self.scratch / "args"

        result = run_send(
            record,
            {
                "PUSHOVER_API_TOKEN": "tok'en",
                "PUSHOVER_USER_KEY": 'us"er',
                "PUSHOVER_TITLE": title,
                "PUSHOVER_MESSAGE": message,
            },
        )

        self.assertFalse(canary.exists(), "an input was executed as shell")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {
            "token": "tok'en",
            "user": 'us"er',
            "title": title,
            "message": message,
        }
        args = load_args(str(record))
        self.assertEqual(problems(args, expected), [])
        # Checked as an argument: a fake server that hangs past 30s would slow every run.
        has_timeout = ("--max-time", "30") in set(zip(args, args[1:]))
        self.assertTrue(has_timeout, "curl was not given --max-time 30")

    def test_rejects_empty_or_unset_input(self) -> None:
        # The runner does not enforce required: true, so an omitted input arrives as an empty string.
        for var in INPUTS:
            for mode in ("empty", "unset"):
                with self.subTest(var=var, mode=mode):
                    record = self.scratch / f"args-{var}-{mode}"
                    inputs = dict(INPUTS)
                    if mode == "empty":
                        inputs[var] = ""
                    else:
                        del inputs[var]

                    result = run_send(record, inputs)

                    self.assertNotEqual(
                        result.returncode, 0, f"send.sh ran with {var} {mode}"
                    )
                    self.assertFalse(
                        record.exists(), f"curl was called with {var} {mode}"
                    )

    def test_exit_status_follows_response(self) -> None:
        curl = real_curl()
        self.assertNotEqual(Path(curl).resolve(), (STUB_DIR / "curl").resolve())
        for status in (200, 400, 429, 500):
            with self.subTest(status=status), fake_pushover(status) as url:
                result = run_send(
                    self.scratch / f"args-http-{status}",
                    INPUTS,
                    CURL_FORWARD_URL=url,
                    CURL_REAL=curl,
                )
                output = result.stdout + result.stderr
                if status == 200:
                    self.assertEqual(result.returncode, 0, output)
                else:
                    self.assertNotEqual(
                        result.returncode, 0, f"send.sh exited 0 on HTTP {status}"
                    )
                    self.assertIn(
                        f"fake error {status}", output, "send.sh hid the response body"
                    )


if __name__ == "__main__":
    unittest.main()
