#!/usr/bin/env python3
"""Do a test run and see if git output changed."""
import subprocess


CONVERT = (
    "./convert-statement.py",
    "--config",
    "test/data/config.toml",
)

GIT_STATUS = (
    "git",
    "diff",
    "--exit-code",
    "test/data/out/",
)


def main() -> None:
    """Run program."""
    subprocess.run(CONVERT, check=True)
    subprocess.run(GIT_STATUS, check=True)


if __name__ == "__main__":
    main()
