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


def average_histories(histories):
    """Average generation-wise progress across multiple runs."""
    if not histories:
        return []

    max_length = max(len(history) for history in histories)
    averaged = []

    for generation_idx in range(max_length):
        points = [history[generation_idx] for history in histories if generation_idx < len(history)]
        averaged.append(
            {
                "generation": points[0]["generation"],
                "evaluations": points[0]["evaluations"],
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
    fitnesses,
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
    """Build the final result dictionary returned by one EA run."""
    return {
        "problem_id": problem_id,
        "problem_name": problem_name,
        "dimension": dimension,
        "best_fitness": best_y,
        "best_solution": best_x,
        "final_mean_fitness": float(np.mean(fitnesses)),
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
