import numpy as np


def tournament_score(fitness: float, violation: float, violation_weight: float) -> float:
    """Score one individual for tournament ranking."""
    return fitness - violation_weight * violation


def tournament_select(population, fitnesses, violations, tournament_size: int, rng: np.random.Generator, violation_weight: float):
    """Pick one parent by tournament selection."""
    indices = rng.integers(0, len(population), size=tournament_size)
    best_idx = int(indices[0])
    best_fitness = fitnesses[best_idx]
    best_score = tournament_score(best_fitness, violations[best_idx], violation_weight)

    for idx in indices[1:]:
        idx = int(idx)
        current_fitness = fitnesses[idx]
        current_score = tournament_score(current_fitness, violations[idx], violation_weight)
        if current_score > best_score or (current_score == best_score and current_fitness > best_fitness):
            best_idx = idx
            best_fitness = current_fitness
            best_score = current_score

    return population[best_idx]  # 返回一轮锦标赛的最佳个体
