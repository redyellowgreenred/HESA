from dataclasses import dataclass
from typing import Any

import numpy as np
from ioh import suite

//配置中心
@dataclass
class EASetup://将参数打包成一个对象
    problem: Any
    rng: np.random.Generator
    dimension: int
    one_prob: float
    mutation_rate: float
    pop_size: int
    tournament_size: int
    elite_size: int


def load_problem(problem_id: int):
    """Load one submodular problem from IOH."""
    return next(iter(suite.Submodular([problem_id], [1], [1])))


def default_one_prob(problem_id: int) -> float:
    """Use sparser initialization for MaxCoverage and denser initialization for MaxCut."""
    return 0.05 if 2100 <= problem_id <= 2127 else 0.5


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

    problem = load_problem(problem_id)//加载问题实例
    rng = np.random.default_rng(seed)//创建随机数生成器
    dimension = problem.meta_data.n_variables//问题维度

    if one_prob is None:
        one_prob = default_one_prob(problem_id)

    if mutation_rate is None:
        mutation_rate = 1.0 / dimension//默认每个位发生变异的概率为1/dimension

    pop_size = min(pop_size, budget)//种群大小不能超过预算
    tournament_size = max(2, min(tournament_size, pop_size))//锦标赛选择的大小至少为2,不能超过种群大小
    elite_size = max(0, min(elite_size, pop_size - 1))//精英数量至少为0,不能超过种群大小-1
    mutation_rate = max(0.0, min(1.0, mutation_rate))//变异率在0和1之间

    return EASetup(
        problem=problem,
        rng=rng,
        dimension=dimension,
        one_prob=one_prob,
        mutation_rate=mutation_rate,
        pop_size=pop_size,
        tournament_size=tournament_size,
        elite_size=elite_size,
    )
