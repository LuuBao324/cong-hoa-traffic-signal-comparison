"""Rebuild dataset.csv and comparison tables from the recorded simulation outputs."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_study.dataset import BASE, export_dataset, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sources(), default="dataset_pure_nonrl")
    args = parser.parse_args()
    data = export_dataset(BASE / args.source)
    print(
        f"Exported {len(data['runs'])} runs and {len(data['rows'])} tracked journeys to dataset.csv"
    )


if __name__ == "__main__":
    main()
