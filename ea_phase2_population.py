from dataclasses import dataclass

import numpy as np


@dataclass
class PopulationState:
    population: list[list[int]]
    fitnesses: list[float]
    best_x: list[int]
    best_y: float


def sample_random_solution(n: int, rng: np.random.Generator, one_prob: float):
    """Create a random 0-1 vector."""
    return (rng.random(n) < one_prob).astype(int).tolist()


def initialize_population(problem, rng: np.random.Generator, n: int, pop_size: int, one_prob: float):
    """Create the initial population and record the initial best solution."""
    population = []
    fitnesses = []

    for _ in range(pop_size):
        x = sample_random_solution(n, rng, one_prob)
        y = float(problem(x))
        population.append(x)
        fitnesses.append(y)

    best_idx = int(np.argmax(fitnesses))
    return PopulationState(
        population=population,
        fitnesses=fitnesses,
        best_x=population[best_idx][:],
        best_y=fitnesses[best_idx],
    )
