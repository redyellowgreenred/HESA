def select_elite_survivors(population, fitnesses, elite_size: int):
    """Keep the best elite_size individuals for the next generation."""
    ranked_indices = sorted(range(len(population)), key=lambda idx: fitnesses[idx], reverse=True)
    next_population = [population[idx][:] for idx in ranked_indices[:elite_size]]
    next_fitnesses = [fitnesses[idx] for idx in ranked_indices[:elite_size]]
    return next_population, next_fitnesses
