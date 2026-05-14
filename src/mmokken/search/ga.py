"""Genetic-algorithm-based item selection for AISP.

Original R / C++ source:
- r_reference/mokken_3.1.2/mokken/R/search.ga.R
- r_reference/mokken_3.1.2/mokken/src/geneticAlgorithm.cpp::runGeneticAlgorithm
  (Author: J. H. Straat; Rcpp version: D. van den Bergh)

Port strategy
-------------
Pure-Python implementation, not a pybind11 bridge. Rationale (see ADR 0001
and migration_journal entry 13):

* R's GA uses R's internal RNG state; bit-for-bit equivalence is impossible
  regardless of the bridge approach, so the acceptance test is distributional
  (mean fitness, partition distance over N runs) — not numerical.
* The multidimensional generalisation of AISP (Track B2) will not be a
  parameter change to this algorithm; it is a different algorithm. A C++
  bridge in B1 has no carryover value to B2.
* JSS readers and methodology reviewers benefit from a transparent
  implementation.

Performance is adequate for typical inputs (n_items ≤ 200). If profiling on
bootstrap workloads later flags the inner loop as hot, selective
``@numba.njit`` on :func:`_evaluate_member` is the right escalation.

Algorithm outline (mirrors ``geneticAlgorithm.cpp``):
1. Initial population
   1.1 Randomly draw the initial population
   1.2 Evaluate Mokken scale criteria per individual (repair if violated)
   1.3 Store the best partitioning of the initial population
2. Repeat until no new best is found for ``maxgens`` generations:
   2.1 Selection: roulette wheel from members of the old population
   2.2 Crossover: exchange equivalent subvectors of two members
   2.3 Mutation: randomly change some assignments
   2.4 Evaluate (and repair) the new population
   2.5 Compare to stored best; elitist replacement of worst member
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _compute_matrices(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute VAR, MAXVAR and SijMatrix used by the GA fitness checks.

    Source: R/search.ga.R lines 12-14.
    """
    var = np.cov(x, rowvar=False, ddof=1)
    sorted_x = np.sort(x, axis=0)
    max_var = np.cov(sorted_x, rowvar=False, ddof=1)
    col_var = np.var(x, axis=0, ddof=1)
    sij = np.outer(col_var, col_var)
    return var, max_var, sij


def _scale_num_items(member: np.ndarray, nclus: int) -> np.ndarray:
    """Items per scale (1..nclus). Singleton scales collapse to scale 0.

    Source: ScaleNumItemsRcpp (C++ lines 40-65).
    """
    counts = np.zeros(nclus, dtype=int)
    for k in range(1, nclus + 1):
        counts[k - 1] = int((member == k).sum())
    for k in range(nclus):
        if counts[k] == 1:
            # Singleton -> unscalable
            member[member == k + 1] = 0
            counts[k] = 0
    return counts


def _items_per_scale(member: np.ndarray, counts: np.ndarray, n_item: int) -> np.ndarray:
    """Build (nclus x n_item) matrix: scale k row lists its item indices.

    Source: ScaleItemsRcpp (C++ lines 92-113).
    """
    nclus = counts.size
    items = np.zeros((nclus, n_item), dtype=int)
    for k in range(nclus):
        if counts[k] > 1:
            picked = np.where(member == k + 1)[0]
            items[k, : picked.size] = picked
    return items


def _coef_hi_for_scale(
    items: np.ndarray,
    scale: int,
    n_items_in_scale: int,
    var: np.ndarray,
    max_var: np.ndarray,
) -> np.ndarray:
    """Hi coefficients for the items in a given scale.

    Source: CoefHiRcpp (C++ lines 177-218).
    """
    out = np.zeros(n_items_in_scale, dtype=float)
    for i in range(n_items_in_scale):
        a = int(items[scale, i])
        s_sum = 0.0
        smax_sum = 0.0
        for j in range(n_items_in_scale):
            if i == j:
                continue
            b = int(items[scale, j])
            s_sum += var[b, a]
            smax_sum += max_var[b, a]
        out[i] = s_sum / smax_sum if smax_sum > 1e-6 else 0.0
    return out


def _criterion2(
    member: np.ndarray,
    scale: int,
    counts: np.ndarray,
    items: np.ndarray,
    critval: float,
    var: np.ndarray,
    max_var: np.ndarray,
) -> None:
    """Remove items with Hi < critval until all pass or scale dissolves.

    Source: Criterion2Rcpp (C++ lines 227-287). Mutates inputs in place.
    """
    while True:
        n_in = counts[scale]
        if n_in < 2:
            return
        hi = _coef_hi_for_scale(items, scale, n_in, var, max_var)
        order = np.argsort(hi, kind="stable")  # ascending
        if hi[order[0]] >= critval:
            return
        if n_in == 2:
            # Dissolve the scale entirely
            for k in range(2):
                idx = int(items[scale, k])
                member[idx] = 0
                items[scale, k] = 0
            counts[scale] = 0
            return
        # Remove the item with smallest Hi
        worst_pos = int(order[0])
        worst_item = int(items[scale, worst_pos])
        member[worst_item] = 0
        # Shift items down
        for p in range(worst_pos, n_in - 1):
            items[scale, p] = items[scale, p + 1]
        items[scale, n_in - 1] = 0
        counts[scale] -= 1


def _test_hi(
    member: np.ndarray,
    scale: int,
    counts: np.ndarray,
    items: np.ndarray,
    sij: np.ndarray,
    n_pers: int,
    var: np.ndarray,
    z_cv: float,
) -> None:
    """Remove items with Zi <= z_cv until all pass or scale dissolves.

    Source: TestHiRcpp (C++ lines 295-375).
    """
    while True:
        n_in = counts[scale]
        if n_in < 2:
            return
        zi = np.zeros(n_in, dtype=float)
        for i in range(n_in):
            a = int(items[scale, i])
            sum_sij = 0.0
            s = 0.0
            for j in range(n_in):
                if i == j:
                    continue
                b = int(items[scale, j])
                sum_sij += sij[a, b]
                s += var[a, b]
            zi[i] = s * np.sqrt(n_pers - 1) / np.sqrt(sum_sij) if sum_sij > 1e-6 else 0.0
        order = np.argsort(zi, kind="stable")
        if zi[order[0]] > z_cv:
            return
        if n_in == 2:
            for k in range(2):
                idx = int(items[scale, k])
                member[idx] = 0
                items[scale, k] = 0
            counts[scale] = 0
            return
        worst_pos = int(order[0])
        worst_item = int(items[scale, worst_pos])
        member[worst_item] = 0
        for p in range(worst_pos, n_in - 1):
            items[scale, p] = items[scale, p + 1]
        items[scale, n_in - 1] = 0
        counts[scale] -= 1


def _test_hij(
    member: np.ndarray,
    scale: int,
    counts: np.ndarray,
    items: np.ndarray,
    hij: np.ndarray,
    rng: np.random.Generator,
) -> None:
    """Remove items pairwise if any Hij < 0 (random tie-break).

    Source: testHijRcpp (C++ lines 385-443).
    """
    n_in = counts[scale]
    for i in range(n_in):
        if counts[scale] != n_in:  # already mutated
            n_in = counts[scale]
            if n_in < 2:
                return
        if i >= counts[scale]:
            break
        a = int(items[scale, i])
        j = i + 1
        while j < counts[scale]:
            b = int(items[scale, j])
            if hij[a, b] < 0:
                if counts[scale] == 2:
                    for k in range(2):
                        idx = int(items[scale, k])
                        member[idx] = 0
                        items[scale, k] = 0
                    counts[scale] = 0
                    return
                # Random tie-break
                if rng.random() < 0.5:
                    member[a] = 0
                    drop_pos = i
                else:
                    member[b] = 0
                    drop_pos = j
                for p in range(drop_pos, counts[scale] - 1):
                    items[scale, p] = items[scale, p + 1]
                items[scale, counts[scale] - 1] = 0
                counts[scale] -= 1
                # restart inner loop with current scale's item list
                return _test_hij(member, scale, counts, items, hij, rng)
            j += 1


def _evaluate_member(
    member: np.ndarray,
    nclus: int,
    n_item: int,
    n_pers: int,
    var: np.ndarray,
    max_var: np.ndarray,
    hij: np.ndarray,
    sij: np.ndarray,
    critval: float,
    z_cv: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, float]:
    """Apply Mokken-scale repairs and compute the fitness of one member.

    Source: EvaluateRcpp inner loop body (C++ lines 492-544).
    """
    counts = _scale_num_items(member, nclus)
    items = _items_per_scale(member, counts, n_item)
    for k in range(nclus):
        if counts[k] > 1:
            _criterion2(member, k, counts, items, critval, var, max_var)
        if counts[k] > 1:
            _test_hi(member, k, counts, items, sij, n_pers, var, z_cv)
        if counts[k] > 1:
            _test_hij(member, k, counts, items, hij, rng)

    # Reassign labels so the largest scale gets 1, next 2, ... (descending)
    order = np.argsort(-counts, kind="stable")
    new_member = np.zeros_like(member)
    for new_label, old_idx in enumerate(order):
        if counts[old_idx] > 1:
            new_member[member == old_idx + 1] = new_label + 1
    # Fitness: sum_k n_item^(-(k+1)) * NUMITEMS[order[k]]
    fitness = 0.0
    for k in range(nclus):
        fitness += float(n_item) ** -(k + 1) * counts[order[k]]
    return new_member, fitness


def _initialize_population(
    rng: np.random.Generator, popsize: int, n_item: int, nclus: int
) -> np.ndarray:
    """Random initial population. Returns (popsize, n_item) int array.

    Source: InitializeRcpp (C++ lines 448-454).
    """
    return rng.integers(1, nclus + 1, size=(popsize, n_item), dtype=int)


def _selection(
    pop: np.ndarray, fitness: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Roulette-wheel selection.

    Source: SelectionRcpp (C++ lines 557-605).
    """
    popsize = pop.shape[0]
    total = fitness.sum()
    if total <= 0:
        return pop.copy()
    cumulative = np.cumsum(fitness / total)
    draws = rng.random(popsize)
    chosen = np.searchsorted(cumulative, draws, side="right")
    chosen = np.clip(chosen, 0, popsize - 1)
    return pop[chosen].copy()


def _crossover(
    pop: np.ndarray, pxover: float, rng: np.random.Generator
) -> None:
    """Two-point crossover (mutates in place).

    Source: CrossoverRcpp (C++ lines 614-681).
    """
    popsize, n_item = pop.shape
    flips = rng.random(popsize) < pxover
    chosen = np.where(flips)[0]
    if chosen.size % 2 == 1:
        chosen = chosen[:-1]
    for k in range(0, chosen.size, 2):
        a, b = int(chosen[k]), int(chosen[k + 1])
        p1 = int(rng.integers(0, n_item))
        p2 = int(rng.integers(0, n_item))
        if p1 < p2:
            tmp = pop[a, p1 : p2 + 1].copy()
            pop[a, p1 : p2 + 1] = pop[b, p1 : p2 + 1]
            pop[b, p1 : p2 + 1] = tmp
        elif p1 > p2:
            # outer wrap: swap [0..p2] and [p1..end]
            tmp = pop[a, : p2 + 1].copy()
            pop[a, : p2 + 1] = pop[b, : p2 + 1]
            pop[b, : p2 + 1] = tmp
            tmp = pop[a, p1:].copy()
            pop[a, p1:] = pop[b, p1:]
            pop[b, p1:] = tmp
        else:
            tmp = pop[a, p1]
            pop[a, p1] = pop[b, p1]
            pop[b, p1] = tmp


def _mutation(
    pop: np.ndarray, pmutation: float, nclus: int, rng: np.random.Generator
) -> None:
    """Mutation: each element flips to a different scale with probability pmutation.

    Source: MutationRcpp (C++ lines 689-745). Mirrors the C++ behaviour of
    drawing among ``1..(nscales+1)`` where ``nscales`` is the count of
    distinct non-zero scales currently present in the member.
    """
    popsize, n_item = pop.shape
    mat = rng.random((popsize, n_item))
    for i in range(popsize):
        # Count current distinct scale labels in [1..nclus]
        present = set(int(v) for v in pop[i] if v >= 1)
        nscales = len(present)
        for j in range(n_item):
            if mat[i, j] < pmutation:
                old = int(pop[i, j])
                # Draw among 1..(nscales+1), retry while equal to old
                ceil_lab = nscales + 1
                while True:
                    new_val = int(rng.integers(1, ceil_lab + 1))
                    if new_val != old:
                        pop[i, j] = new_val
                        if new_val > nscales:
                            nscales += 1
                        break


def _keep_the_best(
    pop: np.ndarray,
    fitness: np.ndarray,
    elite_member: np.ndarray,
    elite_fitness: float,
    no_improvement_counter: int,
) -> tuple[np.ndarray, float, int]:
    """Track the best member ever seen.

    Source: KeepTheBestRcpp (C++ lines 754-793).
    """
    cur_best = int(np.argmax(fitness))
    cur_best_fitness = float(fitness[cur_best])
    if cur_best_fitness > elite_fitness:
        elite_member = pop[cur_best].copy()
        elite_fitness = cur_best_fitness
        no_improvement_counter = 0
    return elite_member, elite_fitness, no_improvement_counter


def _elitist(pop: np.ndarray, fitness: np.ndarray, elite_member: np.ndarray, elite_fitness: float) -> None:
    """Replace worst member of pop with elite if current best < elite.

    Source: ElitistRcpp (C++ lines 808-837).
    """
    cur_best = float(fitness.max())
    if cur_best < elite_fitness:
        worst = int(np.argmin(fitness))
        pop[worst] = elite_member.copy()
        fitness[worst] = elite_fitness


def _evaluate_population(
    pop: np.ndarray,
    nclus: int,
    n_item: int,
    n_pers: int,
    var: np.ndarray,
    max_var: np.ndarray,
    hij: np.ndarray,
    sij: np.ndarray,
    critval: float,
    z_cv: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Repair every member and return the fitness vector.

    Source: EvaluateRcpp (C++ lines 463-547).
    """
    popsize = pop.shape[0]
    fitness = np.zeros(popsize, dtype=float)
    for m in range(popsize):
        member = pop[m].copy()
        new_member, f = _evaluate_member(
            member, nclus, n_item, n_pers, var, max_var, hij, sij, critval, z_cv, rng
        )
        pop[m] = new_member
        fitness[m] = f
    return fitness


def search_ga(
    X,
    lowerbound: float = 0.3,
    alpha: float = 0.05,
    popsize: int = 20,
    maxgens: int | None = None,
    pxover: float = 0.5,
    pmutation: float = 0.1,
    *,
    random_state: int | np.random.Generator | None = None,
    verbose: bool = False,
) -> np.ndarray:
    """Genetic-algorithm item selection — pure-Python port of `search.ga`.

    Parameters mirror the R interface (``aisp(..., search='ga')``); see
    :file:`r_reference/.../man/aisp.Rd` for semantics. ``random_state``
    accepts an integer seed or an existing ``numpy.random.Generator`` for
    reproducibility within Python — R's global RNG is not bridged.

    Returns
    -------
    ndarray
        1-D integer array of length ``n_items``. Entry 0 means "unscalable";
        entries ≥ 1 are scale labels with 1 = largest scale.
    """
    x = np.asarray(X, dtype=float)
    n_pers, n_item = x.shape

    if n_item < 2:
        raise ValueError("GA AISP requires at least 2 items")

    if maxgens is None:
        # R default heuristic from aisp.R
        maxgens = int((10 ** (np.log2(n_item / 5.0))) * 1000)

    # iter heuristic from search.ga.R
    if n_item <= 10:
        iter_ = maxgens
    elif n_item <= 20:
        iter_ = 5000
    else:
        iter_ = int(round(4000 / (n_item / 20)))
    iter_ = min(iter_, maxgens)

    var, max_var, sij = _compute_matrices(x)
    # HijMatrix only filled where VAR > 1e-7
    hij = np.zeros_like(var)
    mask = var > 1e-7
    hij[mask] = var[mask] / max_var[mask]

    z_cv = float(norm.ppf(1.0 - alpha))
    nclus = n_item // 2

    if isinstance(random_state, np.random.Generator):
        rng = random_state
    else:
        rng = np.random.default_rng(random_state)

    # Initial population — keep drawing until we have a non-degenerate fitness sum
    population = _initialize_population(rng, popsize, n_item, nclus)
    fitness = _evaluate_population(
        population, nclus, n_item, n_pers, var, max_var, hij, sij, critval=lowerbound, z_cv=z_cv, rng=rng
    )
    attempts = 1
    while fitness.sum() == 0:
        population = _initialize_population(rng, popsize, n_item, nclus)
        fitness = _evaluate_population(
            population, nclus, n_item, n_pers, var, max_var, hij, sij,
            critval=lowerbound, z_cv=z_cv, rng=rng,
        )
        attempts += 1
        if attempts >= maxgens:
            if verbose:
                print(f"No partitioning was found in {maxgens} populations")
            return np.zeros(n_item, dtype=int)

    elite_member = population[int(np.argmax(fitness))].copy()
    elite_fitness = float(fitness.max())
    no_improvement = 0

    for _gen in range(iter_):
        population = _selection(population, fitness, rng)
        _crossover(population, pxover, rng)
        _mutation(population, pmutation, nclus, rng)
        fitness = _evaluate_population(
            population, nclus, n_item, n_pers, var, max_var, hij, sij,
            critval=lowerbound, z_cv=z_cv, rng=rng,
        )
        elite_member, elite_fitness, no_improvement = _keep_the_best(
            population, fitness, elite_member, elite_fitness, no_improvement
        )
        _elitist(population, fitness, elite_member, elite_fitness)
        no_improvement += 1
        # Stop early if a perfect-fitness partition emerges (all items in scale 1)
        if elite_fitness >= 1.0:
            break

    return elite_member.astype(int)
