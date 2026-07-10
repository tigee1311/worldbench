"""Generate the deterministic synthetic fixture used for local development."""

from __future__ import annotations

import argparse
from pathlib import Path

from worldbench.backends.demo import DemoBackend


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", nargs="?", type=Path, default=Path("examples/demo_dataset")
    )
    args = parser.parse_args()
    print(DemoBackend().create(args.output))


if __name__ == "__main__":
    main()
