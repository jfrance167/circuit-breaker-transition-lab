"""Create only new invented demo inputs; existing directories are preserved."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.support import cases  # noqa: E402


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 2
    failed = False
    try:
        # Validate frozen provenance before creating a directory or any file.
        fixtures = cases()
        target = Path(args[0])
        target.mkdir(parents=False, exist_ok=False)
        for case in fixtures:
            with (target / (case["name"] + ".json")).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(case["input"], indent=2) + "\n")
    except (OSError, ValueError):
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
