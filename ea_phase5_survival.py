from ea_phase2_population import solution_sort_key


def select_elite_survivors(population, fitnesses, violations, penalties, elite_size: int, prefer_feasible: bool = False):
    """Keep the best elite_size individuals for the next generation."""
    ranked_indices = sorted(
        range(len(population)),
        key=lambda idx: solution_sort_key(fitnesses[idx], violations[idx], penalties[idx], prefer_feasible),
        reverse=True,
    )
    next_population = [population[idx][:] for idx in ranked_indices[:elite_size]]
    next_fitnesses = [fitnesses[idx] for idx in ranked_indices[:elite_size]]
    next_violations = [violations[idx] for idx in ranked_indices[:elite_size]]
    next_penalties = [penalties[idx] for idx in ranked_indices[:elite_size]]
    return next_population, next_fitnesses, next_violations, next_penalties
