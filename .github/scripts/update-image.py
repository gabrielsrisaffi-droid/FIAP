"""Update exactly one ECR image reference in a Kubernetes manifest."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()

    content = args.manifest.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?m)^(\s*image:\s*)([\"']?){re.escape(args.repository)}"
        rf":[^\s\"']+([\"']?)\s*$"
    )

    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise SystemExit(
            f"Expected one image for {args.repository} in {args.manifest}, "
            f"found {len(matches)}"
        )

    def replacement(match: re.Match[str]) -> str:
        quote = match.group(2) or match.group(3)
        return f"{match.group(1)}{quote}{args.image}{quote}"

    updated = pattern.sub(replacement, content, count=1)
    args.manifest.write_text(updated, encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
