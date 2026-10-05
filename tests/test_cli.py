import contextlib
import io
import json
from pathlib import Path
import subprocess  # nosec B404: fixed reviewed local Python module in synthetic child tests.
import sys
import tempfile
import unittest
from unittest.mock import patch

from breaker_lab.__main__ import emit, error_channel, main, read_input
from breaker_lab.admission import LabError
from tests.support import document, encode

ROOT = Path(__file__).resolve().parents[1]


class Sink:
    def __init__(self, mode):
        self.mode = mode

    def write(self, text):
        if self.mode == "raise":
            raise OSError("invented sink detail")
        if self.mode == "closed":
            raise ValueError("invented closed detail")
        if self.mode == "bool":
            return True
        return len(text) - 1 if self.mode == "short" else len(text)

    def flush(self):
        if self.mode == "flush":
            raise OSError("invented flush detail")


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".test-tmp").mkdir(exist_ok=True)

    def invoke(self, arguments):
        # No shell; argv is the owned module and synthetic fixture paths only.
        return subprocess.run([sys.executable, "-m", "breaker_lab", *arguments],  # nosec B603
                              cwd=ROOT, capture_output=True, timeout=20, check=False)

    def test_valid_denied_trace_exit_zero(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as folder:
            path = Path(folder) / "trace.json"
            path.write_bytes(encode(document(actions=[("attempt",1,0,None),("complete",1,0,"failure"),
                                                      ("attempt",2,1,None)], policy=(1,10,1))))
            child = self.invoke([str(path)])
        self.assertEqual(child.returncode, 0)
        self.assertEqual(child.stderr, b"")
        self.assertEqual(json.loads(child.stdout)["summary"]["denied"], 1)

    def test_late_invalid_error_has_no_report_or_input(self):
        doc = document(actions=[("attempt",1,1,None),("complete",1,0,"success")])
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as folder:
            path = Path(folder) / "trace.json"
            path.write_bytes(encode(doc))
            child = self.invoke([str(path)])
        self.assertEqual(child.returncode, 2)
        self.assertEqual(child.stdout, b"")
        self.assertEqual(json.loads(child.stderr), {"status": "error", "code": "schema.invalid"})

    def test_arguments_help_and_io(self):
        child = self.invoke(["--invented-private-marker"])
        self.assertEqual(child.returncode, 2)
        self.assertEqual(json.loads(child.stderr)["code"], "arguments.invalid")
        self.assertNotIn(b"invented-private-marker", child.stderr)
        help_child = self.invoke(["--help"])
        self.assertEqual(help_child.returncode, 0)
        self.assertEqual(help_child.stderr, b"")
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as folder:
            for path in (folder, str(Path(folder) / "missing.json")):
                result = self.invoke([path])
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stderr)["code"], "input.io")
                self.assertEqual(result.stdout, b"")

    def test_real_closed_report_and_both_sinks(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as folder:
            path = Path(folder) / "trace.json"
            path.write_bytes(encode(document()))
            for close_error in (False, True):
                child = subprocess.Popen([sys.executable, "-m", "breaker_lab", str(path)],  # nosec B603
                                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    child.stdout.close()
                    if close_error:
                        child.stderr.close()
                    self.assertEqual(child.wait(timeout=20), 2)
                    error = b"" if close_error else child.stderr.read()
                    if not close_error:
                        self.assertEqual(json.loads(error)["code"], "output.error")
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=20)
                    if not child.stderr.closed:
                        child.stderr.close()

    def test_real_closed_diagnostic_sink(self):
        child = subprocess.Popen([sys.executable, "-m", "breaker_lab", "--invalid"],  # nosec B603
                                 cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            child.stderr.close()
            self.assertEqual(child.wait(timeout=20), 2)
            self.assertEqual(child.stdout.read(), b"")
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=20)
            child.stdout.close()

    def test_short_flush_closed_write_errors(self):
        for mode in ("short", "bool", "raise", "closed", "flush"):
            with self.subTest(mode=mode), self.assertRaises(LabError) as caught:
                emit("invented report", Sink(mode))
            self.assertEqual(caught.exception.code, "output.error")
            with patch("sys.stderr", Sink(mode)):
                self.assertFalse(error_channel("input.io"))

    def test_error_channel_code_is_closed(self):
        for bad in (None, "invented-private-marker", True):
            sink = io.StringIO()
            with contextlib.redirect_stderr(sink):
                self.assertTrue(error_channel(bad))
            self.assertEqual(json.loads(sink.getvalue()), {"status": "error", "code": "internal.error"})

    def test_unexpected_error_does_not_reflect(self):
        sink, report = io.StringIO(), io.StringIO()
        with patch("breaker_lab.__main__.read_input", side_effect=RuntimeError("invented-private-marker")):
            with contextlib.redirect_stderr(sink), contextlib.redirect_stdout(report):
                self.assertEqual(main(["invented.json"]), 2)
        self.assertEqual(report.getvalue(), "")
        self.assertEqual(json.loads(sink.getvalue())["code"], "internal.error")

    def test_read_input_bytes_bound(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".test-tmp") as folder:
            path = Path(folder) / "trace.json"
            path.write_bytes(b"0" + b" " * 65535)
            self.assertEqual(len(read_input(path)), 65536)
            path.write_bytes(b"0" + b" " * 65536)
            with self.assertRaises(LabError) as caught:
                read_input(path)
            self.assertEqual(caught.exception.code, "input.limit")

    def test_help_output_failure_is_output_error(self):
        errors = io.StringIO()
        with patch("sys.stdout", Sink("flush")), contextlib.redirect_stderr(errors):
            self.assertEqual(main(["--help"]), 2)
        self.assertEqual(json.loads(errors.getvalue())["code"], "output.error")


if __name__ == "__main__":
    unittest.main()
