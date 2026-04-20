import numpy as np


def tournament_select(population, fitnesses, tournament_size: int, rng: np.random.Generator):
    """Pick one parent by tournament selection."""
    indices = rng.integers(0, len(population), size=tournament_size)
    best_idx = int(indices[0])
    best_fitness = fitnesses[best_idx]

    for idx in indices[1:]:
        idx = int(idx)
        if fitnesses[idx] > best_fitness:
            best_idx = idx
            best_fitness = fitnesses[idx]

    return population[best_idx]
