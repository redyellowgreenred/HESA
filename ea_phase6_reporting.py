import csv
from pathlib import Path

import numpy as np


def should_continue(problem, budget: int) -> bool:
    return problem.state.evaluations < budget


def make_history_row(generation: int, evaluations: int, best_fitness: float, mean_fitness: float):
    return {
        "generation": generation,
        "evaluations": evaluations,
        "best_fitness": best_fitness,
        "mean_fitness": mean_fitness,
    }


def write_csv_rows(path: str, rows):
    if not rows:
        return

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def advance_history_to_evaluations(history, start_idx: int, evaluations: int):
    """Move along one run history until the last point not exceeding the target evaluations."""
    idx = start_idx
    while idx + 1 < len(history) and history[idx + 1]["evaluations"] <= evaluations:
        idx += 1
    return idx


def average_histories(histories):
    """Average progress across runs after aligning by evaluations with carry-forward."""
    if not histories:
        return []

    histories = [sorted(history, key=lambda row: row["evaluations"]) for history in histories]
    min_common_evaluations = max(history[0]["evaluations"] for history in histories)
    evaluation_grid = sorted(
        {
            row["evaluations"]
            for history in histories
            for row in history
            if row["evaluations"] >= min_common_evaluations
        }
    )

    averaged = []
    indices = [0] * len(histories)

    for evaluations in evaluation_grid:
        points = []
        for history_idx, history in enumerate(histories):
            indices[history_idx] = advance_history_to_evaluations(history, indices[history_idx], evaluations)
            points.append(history[indices[history_idx]])

        mean_generation = int(round(np.mean([point["generation"] for point in points])))
        averaged.append(
            {
                "generation": mean_generation,
                "evaluations": evaluations,
                "mean_best_fitness": float(np.mean([point["best_fitness"] for point in points])),
                "mean_population_fitness": float(np.mean([point["mean_fitness"] for point in points])),
            }
        )

    return averaged


def build_run_result(
    problem_id: int,
    problem_name: str,
    dimension: int,
    best_x,
    best_y: float,
    final_mean_fitness: float,
    problem,
    generation: int,
    one_prob: float,
    pop_size: int,
    mutation_rate: float,
    crossover_rate: float,
    tournament_size: int,
    elite_size: int,
    history,
):
    """Build the final result dictionary returned by one solver run."""
    return {
        "problem_id": problem_id,
        "problem_name": problem_name,
        "dimension": dimension,
        "best_fitness": best_y,
        "best_solution": best_x,
        "final_mean_fitness": float(final_mean_fitness),
        "evaluations": problem.state.evaluations,
        "generations": generation,
        "one_prob": one_prob,
        "pop_size": pop_size,
        "mutation_rate": mutation_rate,
        "crossover_rate": crossover_rate,
        "tournament_size": tournament_size,
        "elite_size": elite_size,
        "history": history,
    }
