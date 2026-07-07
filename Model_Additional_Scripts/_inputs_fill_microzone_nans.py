"""Fill missing values in the microzones input file with zero.

By default this updates Model_Inputs/microzones.csv in place and writes a
backup next to it first. The script uses Python's standard csv module so values
that are not missing are passed through unchanged as text.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


MISSING_TOKENS = {"", "nan", "na", "n/a", "null", "none"}


def is_missing(value: str) -> bool:
    return value.strip().lower() in MISSING_TOKENS


def fill_missing_values(input_path: Path, output_path: Path) -> int:
    filled_count = 0

    with input_path.open("r", newline="", encoding="utf-8-sig") as src:
        reader = csv.reader(src)
        rows = []

        for row_index, row in enumerate(reader):
            if row_index == 0:
                rows.append(row)
                continue

            filled_row = []
            for value in row:
                if is_missing(value):
                    filled_row.append("0")
                    filled_count += 1
                else:
                    filled_row.append(value)
            rows.append(filled_row)

    with output_path.open("w", newline="", encoding="utf-8") as dst:
        writer = csv.writer(dst, lineterminator="\n")
        writer.writerows(rows)

    return filled_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=Path("Model_Inputs") / "microzones.csv",
        type=Path,
        help="Source microzones CSV.",
    )
    parser.add_argument(
        "--output",
        default=None,
        type=Path,
        help="Output CSV. Defaults to overwriting --input.",
    )
    parser.add_argument(
        "--backup",
        default=None,
        type=Path,
        help="Backup path for in-place updates.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup when overwriting the input file.",
    )
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output or input_path

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if output_path.resolve() == input_path.resolve() and not args.no_backup:
        backup_path = args.backup or input_path.with_name(
            f"{input_path.stem}_before_fillna{input_path.suffix}"
        )
        shutil.copy2(input_path, backup_path)
        print(f"Backup written to {backup_path}")

    if output_path.resolve() == input_path.resolve():
        temp_path = input_path.with_name(f"{input_path.stem}_fillna_tmp{input_path.suffix}")
        filled_count = fill_missing_values(input_path, temp_path)
        temp_path.replace(input_path)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        filled_count = fill_missing_values(input_path, output_path)

    print(f"Filled {filled_count:,} missing values with 0 in {output_path}")


if __name__ == "__main__":
    main()
