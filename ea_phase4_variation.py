import numpy as np


def uniform_crossover(parent_a, parent_b, rng: np.random.Generator):
    """Create two children with uniform crossover."""
    a = np.asarray(parent_a, dtype=np.int8)
    b = np.asarray(parent_b, dtype=np.int8)
    mask = rng.random(len(a)) < 0.5

    child_a = np.where(mask, a, b).astype(int).tolist()
    child_b = np.where(mask, b, a).astype(int).tolist()
    return child_a, child_b


def bitwise_mutation(individual, rng: np.random.Generator, mutation_rate: float):
    """Flip each bit independently with probability mutation_rate."""
    x = np.asarray(individual, dtype=np.int8).copy()
    flips = rng.random(len(x)) < mutation_rate
    x[flips] = 1 - x[flips]
    return x.astype(int).tolist()
