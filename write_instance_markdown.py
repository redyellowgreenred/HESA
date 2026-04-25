import argparse
import csv
from collections import defaultdict
from pathlib import Path


META_KEYS = [
    "label",
    "version",
    "run_id",
    "family",
    "budget",
    "runs",
    "seed",
    "pop_size",
    "crossover_rate",
    "mutation_rate",
    "one_prob",
    "tournament_size",
    "elite_size",
    "archive_dir",
]

FAMILY_PRIORITY = {
    "MaxCut": 0,
    "MaxCoverage": 1,
}


def read_kv_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def parse_int(value: str) -> int:
    return int(float(value))


def parse_float(value: str) -> float:
    return float(value)


def read_instance_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                {
                    "problem_id": parse_int(row["problem_id"]),
                    "problem_name": row["problem_name"],
                    "family": row["family"],
                    "dimension": parse_int(row["dimension"]),
                    "runs": parse_int(row["runs"]),
                    "budget": parse_int(row["budget"]),
                    "average_best_fitness": parse_float(row["average_best_fitness"]),
                    "std_best_fitness": parse_float(row["std_best_fitness"]),
                    "min_best_fitness": parse_float(row["min_best_fitness"]),
                    "max_best_fitness": parse_float(row["max_best_fitness"]),
                    "average_final_mean_fitness": parse_float(row["average_final_mean_fitness"]),
                    "std_final_mean_fitness": parse_float(row["std_final_mean_fitness"]),
                }
            )
    return rows


def group_rows_by_family(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(row)

    for family_rows in grouped.values():
        family_rows.sort(key=lambda item: item["problem_id"])

    return grouped


def format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)

    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))

    return f"{value:.3f}"


def build_parameter_table(values: dict[str, str]) -> list[str]:
    lines = ["| Parameter | Value |", "| --- | --- |"]
    for key in META_KEYS:
        if key in values:
            lines.append(f"| `{key}` | `{values[key]}` |")
    return lines


def build_family_table(rows) -> list[str]:
    lines = [
        "| Problem ID | Problem Name | n | Runs | Budget | Avg Best | Std Best | Min Best | Max Best | Avg Final Mean | Std Final Mean |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        lines.append(
            "| "
            f"`{row['problem_id']}` | "
            f"`{row['problem_name']}` | "
            f"`{row['dimension']}` | "
            f"`{row['runs']}` | "
            f"`{row['budget']}` | "
            f"`{format_number(row['average_best_fitness'])}` | "
            f"`{format_number(row['std_best_fitness'])}` | "
            f"`{format_number(row['min_best_fitness'])}` | "
            f"`{format_number(row['max_best_fitness'])}` | "
            f"`{format_number(row['average_final_mean_fitness'])}` | "
            f"`{format_number(row['std_final_mean_fitness'])}` |"
        )
    return lines


def main():
    parser = argparse.ArgumentParser(description="Write a markdown table for per-instance final results")
    parser.add_argument("--run-info", required=True, help="Path to the current run info file")
    parser.add_argument("--input-csv", required=True, help="Path to instance_summary.csv")
    parser.add_argument("--output", required=True, help="Markdown output path")
    parser.add_argument("--track-key", default="", help="Run series key, for example full or full-maxcoverage")
    args = parser.parse_args()

    run_info = read_kv_file(Path(args.run_info))
    rows = read_instance_rows(Path(args.input_csv))
    output_path = Path(args.output)
    grouped_rows = group_rows_by_family(rows)
    track_key = args.track_key or run_info.get("formal_track_key") or run_info.get("label") or "run"

    ordered_families = sorted(grouped_rows, key=lambda name: (FAMILY_PRIORITY.get(name, 99), name))

    lines = [
        f"# Instance Final Results: {track_key}",
        "",
        "This file records the final per-instance results used for the experiment report.",
        "Values come from `instance_summary.csv` and correspond to aggregated results over repeated runs.",
        "",
        "## Run Metadata",
        "",
        *build_parameter_table(run_info),
        "",
    ]

    for family in ordered_families:
        lines.extend(
            [
                f"## {family}",
                "",
                *build_family_table(grouped_rows[family]),
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
