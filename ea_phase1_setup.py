from dataclasses import dataclass
from typing import Any

import numpy as np
from ioh import suite

MAXCUT_DEFAULT_ONE_PROB = 0.5
MAXCOVERAGE_FALLBACK_ONE_PROB = 0.01
MAXCOVERAGE_SMALL_DIMENSION_TARGET_INITIAL_ONES = 4.5
MAXCOVERAGE_MEDIUM_DIMENSION_TARGET_INITIAL_ONES = 4.0
MAXCOVERAGE_LARGE_DIMENSION_TARGET_INITIAL_ONES = 3.0
MAXCUT_SELECTION_VIOLATION_WEIGHT = 0.0
MAXCOVERAGE_SELECTION_VIOLATION_WEIGHT = 0.0


@dataclass
class EASetup:
    # 将参数打包成一个对象
    problem: Any
    rng: np.random.Generator
    dimension: int
    one_prob: float
    mutation_rate: float
    pop_size: int
    tournament_size: int
    elite_size: int
    selection_violation_weight: float


def load_problem(problem_id: int):
    """Load one submodular problem from IOH."""
    return next(iter(suite.Submodular([problem_id], [1], [1])))


def default_one_prob(problem_id: int, dimension: int | None = None) -> float:
    """Use dimension-adaptive sparse initialization for MaxCoverage and denser initialization for MaxCut."""
    if 2100 <= problem_id <= 2127:
        if dimension is None or dimension <= 0:
            return MAXCOVERAGE_FALLBACK_ONE_PROB
        if dimension >= 760:
            target_initial_ones = MAXCOVERAGE_LARGE_DIMENSION_TARGET_INITIAL_ONES
        elif dimension >= 595:
            target_initial_ones = MAXCOVERAGE_MEDIUM_DIMENSION_TARGET_INITIAL_ONES
        else:
            target_initial_ones = MAXCOVERAGE_SMALL_DIMENSION_TARGET_INITIAL_ONES
        return min(1.0, target_initial_ones / dimension)
    return MAXCUT_DEFAULT_ONE_PROB


def default_selection_violation_weight(problem_id: int) -> float:
    """Use violation-aware tournament scoring only for MaxCoverage."""
    if 2100 <= problem_id <= 2127:
        return MAXCOVERAGE_SELECTION_VIOLATION_WEIGHT
    return MAXCUT_SELECTION_VIOLATION_WEIGHT


def create_ea_setup(
    problem_id: int,
    budget: int,
    seed: int,
    pop_size: int,
    mutation_rate: float | None,
    tournament_size: int,
    elite_size: int,
    one_prob: float | None,
):
    """Load the problem instance and normalize EA parameters for one run."""
    if budget < 2:
        raise ValueError("budget must be at least 2 for a population-based EA")

    problem = load_problem(problem_id)  # 加载问题实例
    rng = np.random.default_rng(seed)  # 创建随机数生成器
    dimension = problem.meta_data.n_variables  # 问题维度

    if one_prob is None:
        one_prob = default_one_prob(problem_id, dimension)

    if mutation_rate is None:
        mutation_rate = 1.0 / dimension  # 默认每个位发生变异的概率为 1/dimension

    selection_violation_weight = default_selection_violation_weight(problem_id)

    pop_size = min(pop_size, budget)  # 种群大小不能超过预算
    tournament_size = max(2, min(tournament_size, pop_size))  # 锦标赛大小至少为 2，且不能超过种群大小
    elite_size = max(0, min(elite_size, pop_size - 1))  # 精英数量至少为 0，且不能超过种群大小减 1
    mutation_rate = max(0.0, min(1.0, mutation_rate))  # 变异率限制在 [0, 1]

    return EASetup(
        problem=problem,
        rng=rng,
        dimension=dimension,
        one_prob=one_prob,
        mutation_rate=mutation_rate,
        pop_size=pop_size,
        tournament_size=tournament_size,
        elite_size=elite_size,
        selection_violation_weight=selection_violation_weight,
    )
