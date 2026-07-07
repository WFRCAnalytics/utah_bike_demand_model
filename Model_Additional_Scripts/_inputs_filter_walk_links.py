"""Create a pedestrian-only link file for the walk model.

Reads Model_Inputs/links.csv, keeps rows where PedNetwork == "Y", and writes
Model_Inputs/links_walk.csv. The script uses Python's standard csv module so it
does not require pandas.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=Path("Model_Inputs") / "links.csv",
        type=Path,
        help="Source multimodal links CSV.",
    )
    parser.add_argument(
        "--output",
        default=Path("Model_Inputs") / "links_walk.csv",
        type=Path,
        help="Output pedestrian-network links CSV.",
    )
    args = parser.parse_args()

    kept = 0
    total = 0

    with args.input.open("r", newline="", encoding="utf-8-sig") as src:
        reader = csv.DictReader(src)
        if reader.fieldnames is None:
            raise ValueError(f"{args.input} does not contain a header row")
        if "PedNetwork" not in reader.fieldnames:
            raise KeyError(f"{args.input} is missing required column PedNetwork")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as dst:
            writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                if row.get("PedNetwork", "").strip().upper() == "Y":
                    writer.writerow(row)
                    kept += 1

    print(f"Wrote {kept:,} of {total:,} links to {args.output}")


if __name__ == "__main__":
    main()
