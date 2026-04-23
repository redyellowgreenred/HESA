from dataclasses import dataclass

import numpy as np

//种群初始化、记录最优解状态
@dataclass
class PopulationState:
    population: list[list[int]]//个体的集合 其中每个个体是一个0-1向量
    fitnesses: list[float]//每个个体对应的fitness
    best_x: list[int]//最优个体
    best_y: float//最优fitness

//随机生成一个0-1向量
def sample_random_solution(n: int, rng: np.random.Generator, one_prob: float):
    """Create a random 0-1 vector."""
    return (rng.random(n) < one_prob).astype(int).tolist()


def initialize_population(problem, rng: np.random.Generator, n: int, pop_size: int, one_prob: float):
    """Create the initial population and record the initial best solution."""
    population = []
    fitnesses = []

    for _ in range(pop_size):
        x = sample_random_solution(n, rng, one_prob)//生成一个随机解
        y = float(problem(x))//评估这个解的fitness
        population.append(x)//加入种群
        fitnesses.append(y)//加入fitness列表

    best_idx = int(np.argmax(fitnesses))
    return PopulationState(
        population=population,
        fitnesses=fitnesses,
        best_x=population[best_idx][:],
        best_y=fitnesses[best_idx],
    )//获得一个完整的初始种群，同时记录了每个个体的fitness、当前最优个体和最优fitness
