import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


METRIC_LABELS = {
    "mean_best_fitness": "Average Best-So-Far Fitness",
    "mean_population_fitness": "Average Population Fitness",
    "best_fitness": "Best Fitness",
    "mean_fitness": "Population Fitness",
}

FAMILY_COLORS = {
    "MaxCut": "#1f77b4",
    "MaxCoverage": "#d62728",
}


def to_int(value: str) -> int:
    return int(float(value))


def to_float(value: str) -> float:
    return float(value)


def read_curve_csv(path: str):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"No data found in {path}")

    parsed_rows = []
    for row in rows:
        parsed = {}
        for key, value in row.items():
            if key in {"problem_id", "dimension", "generation", "evaluations"} and value != "":
                parsed[key] = to_int(value)
            elif key in {"mean_best_fitness", "mean_population_fitness", "best_fitness", "mean_fitness"} and value != "":
                parsed[key] = to_float(value)
            else:
                parsed[key] = value
        parsed_rows.append(parsed)

    return parsed_rows


def group_rows_by_problem(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = row.get("problem_id", "single_problem")
        grouped[key].append(row)

    for problem_rows in grouped.values():
        problem_rows.sort(key=lambda item: item["evaluations"])

    return grouped


def group_rows_by_family(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get("family", "Unknown")].append(row)
    return grouped


def aggregate_family_curve(problem_curves):
    if not problem_curves:
        return []

    max_len = max(len(curve) for curve in problem_curves)
    aggregated = []

    for idx in range(max_len):
        points = [curve[idx] for curve in problem_curves if idx < len(curve)]
        aggregated.append(
            {
                "generation": points[0]["generation"],
                "evaluations": points[0]["evaluations"],
                "mean_best_fitness": sum(point["mean_best_fitness"] for point in points) / len(points),
                "mean_population_fitness": sum(point["mean_population_fitness"] for point in points) / len(points),
            }
        )

    return aggregated


def sanitize_filename(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def ensure_output_dir(path: str):
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def configure_style():
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.figsize": (12.5, 8.5),
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.titlesize": 13,
            "legend.fontsize": 8,
        }
    )


def plot_metric_axis(ax, curves, x_key: str, metric_key: str, title: str, family_color: str):
    for label, rows, color, alpha, linewidth in curves:
        x_values = [row[x_key] for row in rows]
        y_values = [row[metric_key] for row in rows]
        ax.plot(x_values, y_values, label=label, color=color, alpha=alpha, linewidth=linewidth)

    ax.set_title(title)
    ax.set_xlabel("Evaluations" if x_key == "evaluations" else "Generations")
    ax.set_ylabel(METRIC_LABELS.get(metric_key, title))
    ax.ticklabel_format(style="plain", axis="x")
    ax.grid(True, alpha=0.3)
    ax.set_facecolor("#fbfbfb")
    ax.title.set_color(family_color)


def save_figure(fig, output_base: Path, formats, dpi: int):
    for fmt in formats:
        fig.savefig(output_base.with_suffix(f".{fmt}"), dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def resolve_metric_key(rows, metric: str) -> str:
    if metric == "best":
        return "mean_best_fitness" if "mean_best_fitness" in rows[0] else "best_fitness"
    return "mean_population_fitness" if "mean_population_fitness" in rows[0] else "mean_fitness"


def build_family_curves(rows):
    family_problem_rows = group_rows_by_problem(rows)
    curves = []
    for problem_id, problem_rows in sorted(family_problem_rows.items()):
        label = problem_rows[0].get("problem_name", str(problem_id))
        curves.append((label, problem_rows, None, 0.45, 1.6))

    family_average = aggregate_family_curve([problem_rows for _, problem_rows, _, _, _ in curves])
    return curves, family_average


def plot_family_figure(family: str, rows, output_dir: Path, x_key: str, metric: str, formats, dpi: int):
    family_color = FAMILY_COLORS.get(family, "#333333")
    _, family_average = build_family_curves(rows)
    metric_key = resolve_metric_key(rows, metric)

    fig, ax = plt.subplots(1, 1, figsize=(10.5, 5.8))
    fig.suptitle(f"{family} Average Fitness Curve", fontsize=15, fontweight="bold")

    curves = [("Average Fitness", family_average, family_color, 1.0, 3.0)]

    plot_metric_axis(
        ax,
        curves,
        x_key=x_key,
        metric_key=metric_key,
        title="Average Fitness",
        family_color=family_color,
    )
    ax.set_ylabel("Average Fitness")

    output_base = output_dir / f"{sanitize_filename(family)}_curves"
    save_figure(fig, output_base, formats, dpi)


def plot_single_problem_figure(problem_label: str, rows, output_dir: Path, x_key: str, metric: str, formats, dpi: int):
    fig, ax = plt.subplots(1, 1, figsize=(9, 5.6))
    fig.suptitle(f"{problem_label} Progress Curve", fontsize=15, fontweight="bold")

    line_color = "#1f77b4"
    curves = [(problem_label, rows, line_color, 0.95, 2.5)]
    metric_key = resolve_metric_key(rows, metric)

    plot_metric_axis(
        ax,
        curves,
        x_key=x_key,
        metric_key=metric_key,
        title=METRIC_LABELS.get(metric_key, "Fitness"),
        family_color=line_color,
    )

    output_base = output_dir / sanitize_filename(problem_label)
    save_figure(fig, output_base, formats, dpi)


def main():
    parser = argparse.ArgumentParser(description="Plot assignment-ready curves from EA CSV outputs")
    parser.add_argument(
        "--input-csv",
        type=str,
        default="results/batch_baseline/all_curves.csv",
        help="Curve CSV produced by batch_run.py or main.py",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/plots",
        help="Directory where figures will be saved",
    )
    parser.add_argument(
        "--x-axis",
        choices=["evaluations", "generation"],
        default="evaluations",
        help="X axis for the curve plot",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["png"],
        help="Output formats, for example: --formats png svg pdf",
    )
    parser.add_argument("--dpi", type=int, default=220, help="DPI for raster outputs such as PNG")
    parser.add_argument(
        "--metric",
        choices=["best", "population"],
        default="best",
        help="Which curve to keep in each output figure",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "family", "problem", "both"],
        default="auto",
        help="What level of figures to create",
    )
    args = parser.parse_args()

    configure_style()
    rows = read_curve_csv(args.input_csv)
    output_dir = ensure_output_dir(args.output_dir)
    input_stem = Path(args.input_csv).stem

    has_problem_id = "problem_id" in rows[0]
    has_family = "family" in rows[0]

    mode = args.mode
    if mode == "auto":
        if has_problem_id and has_family:
            mode = "family"
        else:
            mode = "problem"

    generated = []

    if mode in {"family", "both"} and has_problem_id and has_family:
        for family, family_rows in sorted(group_rows_by_family(rows).items()):
            plot_family_figure(family, family_rows, output_dir, args.x_axis, args.metric, args.formats, args.dpi)
            for fmt in args.formats:
                generated.append(output_dir / f"{sanitize_filename(family)}_curves.{fmt}")

    if mode in {"problem", "both"}:
        grouped = group_rows_by_problem(rows)
        for problem_id, problem_rows in sorted(grouped.items()):
            label = problem_rows[0].get("problem_name")
            if not label:
                label = input_stem if problem_id == "single_problem" else str(problem_id)
            plot_single_problem_figure(label, problem_rows, output_dir, args.x_axis, args.metric, args.formats, args.dpi)
            for fmt in args.formats:
                generated.append(output_dir / f"{sanitize_filename(label)}.{fmt}")

    for path in generated:
        print(f"saved_plot={path}")


if __name__ == "__main__":
    main()
