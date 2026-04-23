import argparse
import numpy as np

from ea_phase1_setup import create_ea_setup
from ea_phase2_population import initialize_population
from ea_phase3_selection import tournament_select
from ea_phase4_variation import bitwise_mutation, uniform_crossover
from ea_phase5_survival import select_elite_survivors
from ea_phase6_reporting import (
    average_histories,
    build_run_result,
    make_history_row,
    should_continue,
    write_csv_rows,
)


def run_binary_ea(
    problem_id: int,
    budget: int,
    seed: int,
    pop_size: int,
    crossover_rate: float,
    mutation_rate: float | None,
    tournament_size: int,
    elite_size: int,
    one_prob: float | None,
):
    setup = create_ea_setup(
        problem_id=problem_id,
        budget=budget,
        seed=seed,
        pop_size=pop_size,
        mutation_rate=mutation_rate,
        tournament_size=tournament_size,
        elite_size=elite_size,
        one_prob=one_prob,
    )

    population_state = initialize_population(
        problem=setup.problem,
        rng=setup.rng,
        n=setup.dimension,
        pop_size=setup.pop_size,
        one_prob=setup.one_prob,
    )

    history = [
        make_history_row(
            generation=0,
            evaluations=setup.problem.state.evaluations,
            best_fitness=population_state.best_y,
            mean_fitness=float(np.mean(population_state.fitnesses)),
        )
    ]

    generation = 0

    while should_continue(setup.problem, budget):
        next_population, next_fitnesses = select_elite_survivors(
            population_state.population,
            population_state.fitnesses,
            setup.elite_size,
        )

        while len(next_population) < setup.pop_size and should_continue(setup.problem, budget):
            parent_a = tournament_select(
                population_state.population,
                population_state.fitnesses,
                setup.tournament_size,
                setup.rng,
            )
            parent_b = tournament_select(
                population_state.population,
                population_state.fitnesses,
                setup.tournament_size,
                setup.rng,
            )

            if setup.rng.random() < crossover_rate:
                children = uniform_crossover(parent_a, parent_b, setup.rng)
            else:
                children = (parent_a[:], parent_b[:])

            for child in children:
                if len(next_population) >= setup.pop_size or not should_continue(setup.problem, budget):
                    break

                child = bitwise_mutation(child, setup.rng, setup.mutation_rate)
                fitness = float(setup.problem(child))
                next_population.append(child)
                next_fitnesses.append(fitness)

                if fitness > population_state.best_y:
                    population_state.best_y = fitness
                    population_state.best_x = child[:]

        population_state.population = next_population
        population_state.fitnesses = next_fitnesses
        generation += 1
        history.append(
            make_history_row(
                generation=generation,
                evaluations=setup.problem.state.evaluations,
                best_fitness=population_state.best_y,
                mean_fitness=float(np.mean(population_state.fitnesses)),
            )
        )

    return build_run_result(
        problem_id=problem_id,
        problem_name=setup.problem.meta_data.name,
        dimension=setup.dimension,
        best_x=population_state.best_x,
        best_y=population_state.best_y,
        fitnesses=population_state.fitnesses,
        problem=setup.problem,
        generation=generation,
        one_prob=setup.one_prob,
        pop_size=setup.pop_size,
        mutation_rate=setup.mutation_rate,
        crossover_rate=crossover_rate,
        tournament_size=setup.tournament_size,
        elite_size=setup.elite_size,
        history=history,
    )


def main():
    parser = argparse.ArgumentParser(description="Classic binary EA baseline for IOH submodular problems")
    parser.add_argument("--problem-id", type=int, default=2000, help="2000-2004 for MaxCut, 2100-2127 for MaxCoverage")
    parser.add_argument("--budget", type=int, default=10000, help="Number of fitness evaluations")
    parser.add_argument("--runs", type=int, default=10, help="How many independent runs to do")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed")
    parser.add_argument("--one-prob", type=float, default=None, help="Probability of sampling bit 1 in initialization")
    parser.add_argument("--pop-size", type=int, default=40, help="Population size")
    parser.add_argument("--crossover-rate", type=float, default=0.9, help="Probability of applying uniform crossover")
    parser.add_argument("--mutation-rate", type=float, default=None, help="Bit-wise mutation rate; default is 1/n")
    parser.add_argument("--tournament-size", type=int, default=2, help="Tournament size for parent selection")
    parser.add_argument("--elite-size", type=int, default=1, help="How many best individuals survive each generation")
    parser.add_argument("--curve-csv", type=str, default=None, help="Optional path for averaged progress curve CSV")
    parser.add_argument("--run-csv", type=str, default=None, help="Optional path for per-run summary CSV")
    args = parser.parse_args()

    run_rows = []//存每次运行的结果
    histories = []

    for run_id in range(args.runs):
        result = run_binary_ea(
            problem_id=args.problem_id,
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

        run_rows.append(
            {
                "run": run_id,
                "problem_id": result["problem_id"],
                "problem_name": result["problem_name"],
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
        )

        print(
            f"run={run_id} problem={result['problem_name']} "
            f"n={result['dimension']} pop={result['pop_size']} "
            f"one_prob={result['one_prob']:.3f} mutation={result['mutation_rate']:.6f} "
            f"best={result['best_fitness']} final_mean={result['final_mean_fitness']:.3f} "
            f"gens={result['generations']} evals={result['evaluations']}"
        )

    if args.run_csv:
        write_csv_rows(args.run_csv, run_rows)

    if args.curve_csv:
        averaged_curve = average_histories(histories)
        write_csv_rows(args.curve_csv, averaged_curve)

    print(f"average_best_fitness={float(np.mean([row['best_fitness'] for row in run_rows]))}")
    print(f"average_final_mean_fitness={float(np.mean([row['final_mean_fitness'] for row in run_rows]))}")


if __name__ == "__main__":
    main()
