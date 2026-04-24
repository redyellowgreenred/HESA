import argparse
from pathlib import Path


DISPLAY_KEYS = [
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
    "x_axis",
    "metric",
    "formats",
    "formal_track_key",
]

COMPARE_KEYS = [
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
    "x_axis",
    "metric",
    "formats",
]


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


def format_changes(current: dict[str, str], previous: dict[str, str]) -> list[str]:
    changes = []
    for key in COMPARE_KEYS:
        current_value = current.get(key, "")
        previous_value = previous.get(key, "")
        if current_value != previous_value:
            changes.append(f"- `{key}`: `{previous_value or '(missing)'}` -> `{current_value or '(missing)'}`")
    return changes


def build_parameter_table(values: dict[str, str]) -> list[str]:
    rows = ["| Parameter | Value |", "| --- | --- |"]
    for key in DISPLAY_KEYS:
        if key in values:
            rows.append(f"| `{key}` | `{values[key]}` |")
    for extra_key in ["archive_root", "archive_dir", "latest_plot_dir", "formal_run"]:
        if extra_key in values:
            rows.append(f"| `{extra_key}` | `{values[extra_key]}` |")
    return rows


def build_artifact_list(archive_dir: Path, output_name: str) -> list[str]:
    artifacts = []
    for path in sorted(archive_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".png", ".svg", ".pdf", ".md", ".txt", ".log"}:
            artifacts.append(f"- `{path.name}`")
    if output_name not in {path.name for path in archive_dir.iterdir() if path.is_file()}:
        artifacts.append(f"- `{output_name}`")
    if (archive_dir / "batch_outputs").is_dir():
        artifacts.append("- `batch_outputs/`")
    return artifacts


def main():
    parser = argparse.ArgumentParser(description="Write a markdown summary for one formal experiment run")
    parser.add_argument("--current-info", required=True, help="Path to the current run info file")
    parser.add_argument("--previous-info", required=True, help="Path to the previous formal run info file")
    parser.add_argument("--output", required=True, help="Markdown output path")
    parser.add_argument("--track-key", required=True, help="Formal run series key, for example full-maxcoverage")
    args = parser.parse_args()

    current_info_path = Path(args.current_info)
    previous_info_path = Path(args.previous_info)
    output_path = Path(args.output)

    current = read_kv_file(current_info_path)
    previous = read_kv_file(previous_info_path)
    archive_dir = Path(current["archive_dir"])

    lines = [
        f"# Formal Run Summary: {args.track_key}",
        "",
        f"- Version: `v{current.get('version', '?')}`",
        f"- Run ID: `{current.get('run_id', '?')}`",
        f"- Family: `{current.get('family', '?')}`",
        f"- Archive: `{current.get('archive_dir', '?')}`",
        "",
        "## Current Parameters",
        "",
        *build_parameter_table(current),
        "",
        "## Changes From Previous Version",
        "",
    ]

    if previous:
        changes = format_changes(current, previous)
        if changes:
            lines.extend(changes)
        else:
            lines.append("- No parameter changes compared with the previous formal version.")
        lines.extend(
            [
                "",
                f"Previous archive: `{previous.get('archive_dir', '(unknown)')}`",
            ]
        )
    else:
        lines.append("- This is the first recorded formal run in this series.")

    lines.extend(
        [
            "",
            "## Saved Artifacts",
            "",
            *build_artifact_list(archive_dir, output_path.name),
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
