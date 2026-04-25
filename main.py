import argparse
import numpy as np

from ea_phase1_setup import create_ea_setup, default_one_prob, load_problem
from ea_phase2_population import (
    evaluate_solution,
    initialize_population,
    is_feasible_penalty,
    is_maxcoverage_problem,
    sample_random_solution,
    solution_sort_key,
)
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

MAXCUT_SA_INITIAL_TEMPERATURE_SCALE = 1.1
MAXCUT_SA_FINAL_TEMPERATURE_RATIO = 5e-3
MAXCUT_SA_MIN_TEMPERATURE = 1e-8
MAXCUT_SA_HILL_CLIMBING_THRESHOLD_RATIO = 8e-2
MAXCOVERAGE_REPAIR_SAMPLE_SIZE = 4


def sample_candidate_indices(indices: list[int], sample_size: int, rng: np.random.Generator):
    """Sample a small candidate subset without replacement."""
    if len(indices) <= sample_size:
        return indices[:]
    return rng.choice(indices, size=sample_size, replace=False).tolist()


def repair_maxcoverage_child(problem, child, fitness, violation, penalty, rng: np.random.Generator, budget: int):
    """Repair an infeasible MaxCoverage child by removing a few selected bits."""
    if is_feasible_penalty(penalty):
        return child, fitness, violation, penalty

    repaired_child = child[:]
    repaired_fitness = fitness
    repaired_violation = violation
    repaired_penalty = penalty

    while not is_feasible_penalty(repaired_penalty) and should_continue(problem, budget):
        selected_indices = [idx for idx, bit in enumerate(repaired_child) if bit == 1]
        if not selected_indices:
            break

        candidate_indices = sample_candidate_indices(selected_indices, MAXCOVERAGE_REPAIR_SAMPLE_SIZE, rng)

        best_candidate = None
        best_key = None

        for idx in candidate_indices:
            if not should_continue(problem, budget):
                break

            trial = repaired_child[:]
            trial[idx] = 0
            trial_fitness, trial_violation, trial_penalty = evaluate_solution(problem, trial)
            trial_key = solution_sort_key(trial_fitness, trial_violation, trial_penalty, prefer_feasible=True)

            if best_candidate is None or trial_key > best_key:
                best_candidate = (trial, trial_fitness, trial_violation, trial_penalty)
                best_key = trial_key

        if best_candidate is None:
            break

        repaired_child, repaired_fitness, repaired_violation, repaired_penalty = best_candidate

    return repaired_child, repaired_fitness, repaired_violation, repaired_penalty

def flip_vertex(individual, vertex_idx: int):
    """Return a copy with one vertex moved to the opposite side of the cut."""
    candidate = individual[:]
    candidate[vertex_idx] = 1 - candidate[vertex_idx]
    return candidate


def calibrate_maxcut_sa_temperature(current_fitness: float, dimension: int):
    """Choose a temperature scale from the current cut value per vertex."""
    base_temperature = max(1.0, abs(current_fitness) / max(1, dimension))
    return MAXCUT_SA_INITIAL_TEMPERATURE_SCALE * base_temperature


def run_maxcut_sa(
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
    """Solve MaxCut with fixed-order 1-flip simulated annealing."""
    if budget < 1:
        raise ValueError("budget must be at least 1")

    problem = load_problem(problem_id)
    rng = np.random.default_rng(seed)
    dimension = problem.meta_data.n_variables

    if one_prob is None:
        one_prob = default_one_prob(problem_id)

    if mutation_rate is None:
        mutation_rate = 1.0 / dimension

    # Keep the legacy EA parameters in the interface for compatibility, but MaxCut-SA
    # now follows a pure single-solution 1-flip search and starts from one random solution.
    current_x = sample_random_solution(dimension, rng, one_prob)
    current_y, _, _ = evaluate_solution(problem, current_x)
    best_x = current_x[:]
    best_y = current_y

    history = [
        make_history_row(
            generation=0,
            evaluations=problem.state.evaluations,
            best_fitness=best_y,
            mean_fitness=current_y,
        )
    ]

    generation = 0
    remaining_steps = budget - problem.state.evaluations

    if remaining_steps > 0:
        initial_temperature = calibrate_maxcut_sa_temperature(current_y, dimension)
        final_temperature = max(MAXCUT_SA_MIN_TEMPERATURE, initial_temperature * MAXCUT_SA_FINAL_TEMPERATURE_RATIO)
        hill_climbing_temperature = max(
            final_temperature,
            initial_temperature * MAXCUT_SA_HILL_CLIMBING_THRESHOLD_RATIO,
        )
        estimated_rounds = max(1, int(np.ceil(remaining_steps / max(1, dimension))))
        cooling_factor = 1.0

        if estimated_rounds > 1 and initial_temperature > final_temperature:
            cooling_factor = (final_temperature / initial_temperature) ** (1.0 / (estimated_rounds - 1))

        temperature = initial_temperature

        while should_continue(problem, budget):
            for vertex_idx in range(dimension):
                if not should_continue(problem, budget):
                    break

                neighbor = flip_vertex(current_x, vertex_idx)
                neighbor_y, _, _ = evaluate_solution(problem, neighbor)
                delta = neighbor_y - current_y

                accept_move = delta >= 0.0
                if not accept_move and temperature > hill_climbing_temperature:
                    accept_move = rng.random() < np.exp(delta / temperature)

                if accept_move:
                    current_x = neighbor
                    current_y = neighbor_y

                if current_y > best_y:
                    best_x = current_x[:]
                    best_y = current_y

                generation += 1
                history.append(
                    make_history_row(
                        generation=generation,
                        evaluations=problem.state.evaluations,
                        best_fitness=best_y,
                        mean_fitness=current_y,
                    )
                )

            temperature = max(final_temperature, temperature * cooling_factor)

    return build_run_result(
        problem_id=problem_id,
        problem_name=problem.meta_data.name,
        dimension=dimension,
        best_x=best_x,
        best_y=best_y,
        final_mean_fitness=current_y,
        problem=problem,
        generation=generation,
        one_prob=one_prob,
        pop_size=1,
        mutation_rate=mutation_rate,
        crossover_rate=crossover_rate,
        tournament_size=tournament_size,
        elite_size=elite_size,
        history=history,
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
    if 2000 <= problem_id <= 2004:
        return run_maxcut_sa(
            problem_id=problem_id,
            budget=budget,
            seed=seed,
            pop_size=pop_size,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            tournament_size=tournament_size,
            elite_size=elite_size,
            one_prob=one_prob,
        )

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
        repair_solution=repair_maxcoverage_child if is_maxcoverage_problem(setup.problem) else None,
        repair_budget=budget,
    )
    prefer_feasible = is_maxcoverage_problem(setup.problem)

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
        next_population, next_fitnesses, next_violations, next_penalties = select_elite_survivors(
            population_state.population,
            population_state.fitnesses,
            population_state.violations,
            population_state.penalties,
            setup.elite_size,
            prefer_feasible=prefer_feasible,
        )

        while len(next_population) < setup.pop_size and should_continue(setup.problem, budget):
            parent_a = tournament_select(
                population_state.population,
                population_state.fitnesses,
                population_state.violations,
                setup.tournament_size,
                setup.rng,
                setup.selection_violation_weight,
            )
            parent_b = tournament_select(
                population_state.population,
                population_state.fitnesses,
                population_state.violations,
                setup.tournament_size,
                setup.rng,
                setup.selection_violation_weight,
            )

            if setup.rng.random() < crossover_rate:
                children = uniform_crossover(parent_a, parent_b, setup.rng)
            else:
                children = (parent_a[:], parent_b[:])

            for child in children:
                if len(next_population) >= setup.pop_size or not should_continue(setup.problem, budget):
                    break

                child = bitwise_mutation(child, setup.rng, setup.mutation_rate)
                fitness, violation, penalty = evaluate_solution(setup.problem, child)

                if prefer_feasible and not is_feasible_penalty(penalty) and should_continue(setup.problem, budget):
                    child, fitness, violation, penalty = repair_maxcoverage_child(
                        setup.problem,
                        child,
                        fitness,
                        violation,
                        penalty,
                        setup.rng,
                        budget,
                    )

                next_population.append(child)
                next_fitnesses.append(fitness)
                next_violations.append(violation)
                next_penalties.append(penalty)

                child_key = solution_sort_key(fitness, violation, penalty, prefer_feasible)
                best_key = solution_sort_key(
                    population_state.best_y,
                    population_state.best_violation,
                    population_state.best_penalty,
                    prefer_feasible,
                )
                if child_key > best_key:
                    population_state.best_y = fitness
                    population_state.best_violation = violation
                    population_state.best_penalty = penalty
                    population_state.best_x = child[:]

        population_state.population = next_population
        population_state.fitnesses = next_fitnesses
        population_state.violations = next_violations
        population_state.penalties = next_penalties

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
        final_mean_fitness=float(np.mean(population_state.fitnesses)),
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
    parser = argparse.ArgumentParser(description="MaxCut uses fixed-order 1-flip simulated annealing; MaxCoverage keeps the binary EA baseline")
    parser.add_argument("--problem-id", type=int, default=2000, help="2000-2004 for MaxCut, 2100-2127 for MaxCoverage")
    parser.add_argument("--budget", type=int, default=10000, help="Number of fitness evaluations")
    parser.add_argument("--runs", type=int, default=10, help="How many independent runs to do")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed")
    parser.add_argument("--one-prob", type=float, default=None, help="Probability of sampling bit 1 in initialization")
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
    parser.add_argument("--curve-csv", type=str, default=None, help="Optional path for averaged progress curve CSV")
    parser.add_argument("--run-csv", type=str, default=None, help="Optional path for per-run summary CSV")
    args = parser.parse_args()

    run_rows = []  # 存每次运行的结果
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
