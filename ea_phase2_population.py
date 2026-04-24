from dataclasses import dataclass

import numpy as np

FEASIBLE_PENALTY_TOLERANCE = 1e-12


@dataclass
class PopulationState:
    population: list[list[int]]  # 个体集合，每个个体是一个 0-1 向量
    fitnesses: list[float]  # 每个个体对应的 fitness
    violations: list[float]  # 每个个体对应的约束违反量
    penalties: list[float]  # 每个个体对应的约束惩罚值
    best_x: list[int]  # 当前最优个体
    best_y: float  # 当前最优 fitness
    best_violation: float  # 当前最优个体的违反量
    best_penalty: float  # 当前最优个体的惩罚值


def sample_random_solution(n: int, rng: np.random.Generator, one_prob: float):
    """Create a random 0-1 vector."""
    return (rng.random(n) < one_prob).astype(int).tolist()


def evaluate_solution(problem, x: list[int]):
    """Evaluate one solution and read the matching constraint information."""
    fitness = float(problem(x))
    violation = float(problem.constraints.violation())
    penalty = float(problem.constraints.penalty())
    return fitness, violation, penalty


def is_maxcoverage_problem(problem) -> bool:
    """Detect whether the current instance belongs to MaxCoverage."""
    return problem.meta_data.name.lower().startswith("maxcoverage")


def is_maxcut_problem(problem) -> bool:
    """Detect whether the current instance belongs to MaxCut."""
    return problem.meta_data.name.lower().startswith("maxcut")


def is_feasible_penalty(penalty: float) -> bool:
    """Treat zero-penalty solutions as feasible, with a small tolerance for floating point noise."""
    return penalty >= -FEASIBLE_PENALTY_TOLERANCE


def solution_sort_key(fitness: float, violation: float, penalty: float, prefer_feasible: bool):
    """Rank solutions either by raw fitness or by feasible-first ordering."""
    if prefer_feasible:
        feasible = 1 if is_feasible_penalty(penalty) else 0
        if feasible:
            return (feasible, fitness, penalty, -violation)
        return (feasible, penalty, fitness, -violation)
    return (fitness, penalty, -violation)


def initialize_population(problem, rng: np.random.Generator, n: int, pop_size: int, one_prob: float):
    """Create the initial population and record the initial best solution."""
    prefer_feasible = is_maxcoverage_problem(problem)
    population = []
    fitnesses = []
    violations = []
    penalties = []

    for _ in range(pop_size):
        x = sample_random_solution(n, rng, one_prob)
        y, violation, penalty = evaluate_solution(problem, x)
        population.append(x)
        fitnesses.append(y)
        violations.append(violation)
        penalties.append(penalty)

    best_idx = max(
        range(len(population)),
        key=lambda idx: solution_sort_key(fitnesses[idx], violations[idx], penalties[idx], prefer_feasible),
    )
    return PopulationState(
        population=population,
        fitnesses=fitnesses,
        violations=violations,
        penalties=penalties,
        best_x=population[best_idx][:],
        best_y=fitnesses[best_idx],
        best_violation=violations[best_idx],
        best_penalty=penalties[best_idx],
    )  # 返回完整初始种群，并记录当前最优个体与 fitness
