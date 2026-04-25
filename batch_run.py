import argparse
import statistics
from pathlib import Path

from main import average_histories, run_binary_ea, write_csv_rows


MAXCUT_IDS = list(range(2000, 2005))
MAXCOVERAGE_IDS = list(range(2100, 2128))


def get_problem_family(problem_id: int) -> str:
    if 2000 <= problem_id <= 2004:
        return "MaxCut"
    if 2100 <= problem_id <= 2127:
        return "MaxCoverage"
    raise ValueError(f"Unsupported problem id: {problem_id}")


def get_problem_ids(family: str, explicit_ids):
    if explicit_ids:
        return explicit_ids
    if family == "maxcut":
        return MAXCUT_IDS
    if family == "maxcoverage":
        return MAXCOVERAGE_IDS
    return MAXCUT_IDS + MAXCOVERAGE_IDS


def summarize_instance(problem_id: int, run_rows):
    best_values = [row["best_fitness"] for row in run_rows]
    mean_values = [row["final_mean_fitness"] for row in run_rows]
    first = run_rows[0]

    return {
        "problem_id": problem_id,
        "problem_name": first["problem_name"],
        "family": get_problem_family(problem_id),
        "dimension": first["dimension"],
        "runs": len(run_rows),
        "budget": first["evaluations"],
        "average_best_fitness": sum(best_values) / len(best_values),
        "std_best_fitness": statistics.pstdev(best_values) if len(best_values) > 1 else 0.0,
        "min_best_fitness": min(best_values),
        "max_best_fitness": max(best_values),
        "average_final_mean_fitness": sum(mean_values) / len(mean_values),
        "std_final_mean_fitness": statistics.pstdev(mean_values) if len(mean_values) > 1 else 0.0,
        "one_prob": first["one_prob"],
        "pop_size": first["pop_size"],
        "mutation_rate": first["mutation_rate"],
        "crossover_rate": first["crossover_rate"],
        "tournament_size": first["tournament_size"],
        "elite_size": first["elite_size"],
    }


def summarize_family(instance_rows):
    grouped = {}
    for row in instance_rows:
        grouped.setdefault(row["family"], []).append(row)

    family_rows = []
    for family, rows in grouped.items():
        family_rows.append(
            {
                "family": family,
                "instances": len(rows),
                "mean_of_instance_average_best": sum(row["average_best_fitness"] for row in rows) / len(rows),
                "mean_of_instance_average_final_mean": sum(row["average_final_mean_fitness"] for row in rows) / len(rows),
            }
        )

    return family_rows


def main():
    parser = argparse.ArgumentParser(description="Batch runner for all IOH submodular assignment instances")
    parser.add_argument(
        "--family",
        choices=["all", "maxcut", "maxcoverage"],
        default="all",
        help="Which problem family to run when --problem-ids is not provided",
    )
    parser.add_argument(
        "--problem-ids",
        type=int,
        nargs="*",
        default=None,
        help="Optional explicit problem ids, for example: --problem-ids 2000 2001 2100",
    )
    parser.add_argument("--budget", type=int, default=10000, help="Number of fitness evaluations per run")
    parser.add_argument("--runs", type=int, default=10, help="Independent runs per instance")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed")
    parser.add_argument("--one-prob", type=float, default=None, help="Optional override for initialization bit probability")
    parser.add_argument("--pop-size", type=int, default=2, help="Population size")
    parser.add_argument("--crossover-rate", type=float, default=0.5, help="Probability of applying uniform crossover")
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=None,
        help="Bit-wise mutation rate; default is 1/n",
    )
    parser.add_argument("--tournament-size", type=int, default=2, help="Tournament size for parent selection")
    parser.add_argument("--elite-size", type=int, default=1, help="How many best individuals survive each generation")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/batch_baseline",
        help="Directory for all batch CSV outputs",
    )
    args = parser.parse_args()

    problem_ids = get_problem_ids(args.family, args.problem_ids)
    output_dir = Path(args.output_dir)
    curve_dir = output_dir / "curves"
    curve_dir.mkdir(parents=True, exist_ok=True)

    all_run_rows = []
    all_curve_rows = []
    instance_rows = []

    total_instances = len(problem_ids)

    for instance_index, problem_id in enumerate(problem_ids, start=1):
        family = get_problem_family(problem_id)
        print(f"[{instance_index}/{total_instances}] problem_id={problem_id} family={family} started", flush=True)

        run_rows = []
        histories = []

        for run_id in range(args.runs):
            result = run_binary_ea(
                problem_id=problem_id,
                budget=args.budget,
                seed=args.seed + run_id,
                pop_size=args.pop_size,
                crossover_rate=args.crossover_rate,
                mutation_rate=args.mutation_rate,
                tournament_size=args.tournament_size,
                elite_size=args.elite_size,
                one_prob=args.one_prob,
            )
            histories.append(result["history"])

            run_row = {
                "problem_id": result["problem_id"],
                "problem_name": result["problem_name"],
                "family": family,
                "run": run_id,
                "dimension": result["dimension"],
                "best_fitness": result["best_fitness"],
                "final_mean_fitness": result["final_mean_fitness"],
                "evaluations": result["evaluations"],
                "generations": result["generations"],
                "one_prob": result["one_prob"],
                "pop_size": result["pop_size"],
                "mutation_rate": result["mutation_rate"],
                "crossover_rate": result["crossover_rate"],
                "tournament_size": result["tournament_size"],
                "elite_size": result["elite_size"],
            }
            run_rows.append(run_row)
            all_run_rows.append(run_row)

            print(
                f"  run={run_id} best={result['best_fitness']} "
                f"final_mean={result['final_mean_fitness']:.3f} evals={result['evaluations']}"
                ,
                flush=True,
            )

        averaged_curve = average_histories(histories)
        curve_rows = []
        for row in averaged_curve:
            curve_row = {
                "problem_id": problem_id,
                "problem_name": run_rows[0]["problem_name"],
                "family": family,
                "dimension": run_rows[0]["dimension"],
                "generation": row["generation"],
                "evaluations": row["evaluations"],
                "mean_best_fitness": row["mean_best_fitness"],
                "mean_population_fitness": row["mean_population_fitness"],
            }
            curve_rows.append(curve_row)
            all_curve_rows.append(curve_row)

        write_csv_rows(str(curve_dir / f"problem_{problem_id}_curve.csv"), curve_rows)

        instance_row = summarize_instance(problem_id, run_rows)
        instance_rows.append(instance_row)
        print(
            f"[{instance_index}/{total_instances}] problem_id={problem_id} finished "
            f"avg_best={instance_row['average_best_fitness']:.3f} "
            f"avg_final_mean={instance_row['average_final_mean_fitness']:.3f}",
            flush=True,
        )

    family_rows = summarize_family(instance_rows)

    write_csv_rows(str(output_dir / "all_runs.csv"), all_run_rows)
    write_csv_rows(str(output_dir / "all_curves.csv"), all_curve_rows)
    write_csv_rows(str(output_dir / "instance_summary.csv"), instance_rows)
    write_csv_rows(str(output_dir / "family_summary.csv"), family_rows)

    print(f"saved_all_runs={output_dir / 'all_runs.csv'}", flush=True)
    print(f"saved_instance_summary={output_dir / 'instance_summary.csv'}", flush=True)
    print(f"saved_family_summary={output_dir / 'family_summary.csv'}", flush=True)
    print(f"saved_curve_dir={curve_dir}", flush=True)


if __name__ == "__main__":
    main()
