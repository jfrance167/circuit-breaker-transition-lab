"""Local synthetic CLI; closed diagnostics and nontransactional output.

File/sink guards are adapted from Jake's reviewed structured-log lab (MIT).
"""

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from .admission import CODES, LabError, MAX_BYTES
from .core import model, render


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise LabError("arguments.invalid")

    def _print_message(self, message, file=None):
        # argparse help shares the checked output boundary, including flush.
        if message:
            emit(message, file if file is not None else sys.stdout)


def read_input(path):
    """Read a bounded stable regular file; races/blocking are not isolated."""
    if not stat.S_ISREG(path.stat().st_mode):
        raise LabError("input.io")
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise LabError("input.io")
        if info.st_size > MAX_BYTES:
            raise LabError("input.limit")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise LabError("input.limit")
    return raw


def emit(output, stream):
    """Short/failed writes are errors; prior bytes cannot be rolled back."""
    failed = False
    try:
        written = stream.write(output)
        if type(written) is not int or written != len(output):
            raise LabError("output.error")
        stream.flush()
    except (OSError, ValueError):
        failed = True
    if failed:
        raise LabError("output.error")


def error_channel(code):
    if type(code) is not str or code not in CODES:
        code = "internal.error"
    try:
        message = json.dumps({"status": "error", "code": code}) + "\n"
        written = sys.stderr.write(message)
        if type(written) is not int or written != len(message):
            return False
        sys.stderr.flush()
    except Exception:
        return False
    return True


def main(argv=None) -> int:
    """Exit 0 for a complete model (denials included), 2 for any error."""
    try:
        cli = Parser(prog="breaker-lab", description="Model invented serial circuit-breaker transitions")
        cli.add_argument("file", type=Path)
        args = cli.parse_args(argv)
        report = model(read_input(args.file))
        emit(render(report), sys.stdout)
        return 0
    except LabError as error:
        error_channel(error.code)
    except OSError:
        error_channel("input.io")
    except Exception:
        error_channel("internal.error")
    return 2


if __name__ == "__main__":
    status = main()
    if status == 2:
        for name in ("stdout", "stderr"):
            try:
                getattr(sys, name).flush()
            except Exception:
                # CPython otherwise changes exit 2 to 120 for dirty failed sinks.
                setattr(sys, name, None)
    raise SystemExit(status)
