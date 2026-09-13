#!/usr/bin/env python3
"""
Darwin's Sudoku: blind variation plus natural selection builds a valid grid.

Nothing in the genes knows the rules. Every individual is 9 chromosomes (rows)
of 9 genes, and every gene is just a random digit 1..9. A chromosome can hold
the same digit several times, and a gene has no idea where it sits or what its
neighbours are. Mutation draws a brand-new random digit; crossover mixes
chromosomes from two parents at random cut points.

The only place the Sudoku rules exist is the environment: the fitness score.
It counts how many distinct digits each row, column, 3x3 box (and, with
--diagonals, each corner-to-corner diagonal) holds. The environment never edits
a grid or tells a gene what to become. It only decides who lives and who has
children. That alone turns noise into a grid that satisfies every rule.

The grids live on a world map (a square that wraps around at the edges), one
grid per territory. A grid can only mate with its neighbours, and a newborn
must win its territory from the grid already living there. Identical copies are
allowed; a successful grid simply spreads outward one territory at a time, so
distant regions keep evolving their own solutions, as real populations do.

Run with --no-selection to switch the environment off and watch the same
randomness go nowhere.

Usage:
    python sudoku.py
    python sudoku.py --diagonals
    python sudoku.py --no-selection -g 2000
    python sudoku.py -w 80 --seed 42
"""

import argparse
import os
import secrets
import sys
import time

import numpy as np

CELLS = 81
POSITIONS = np.arange(9)[None, None, :]
BIT_COUNT = np.array([bin(i).count("1") for i in range(1 << 10)], dtype=np.int16)

# Valid 9x9 Sudoku grids (Felgenhauer & Jarvis, 2005) and every possible grid of
# random digits. Diagonal grids are a subset, so the same bound holds for them.
VALID_SUDOKU_GRIDS = 6_670_903_752_021_072_936_960
POSSIBLE_GRIDS = 9 ** CELLS


# --------------------------------------------------------------------------
# The environment: the only thing that knows the rules
# --------------------------------------------------------------------------

def build_units(diagonals):
    """Groups of 9 cells that must each hold 1..9 exactly once."""
    units = []
    for i in range(9):
        units.append([i * 9 + c for c in range(9)])           # row
        units.append([r * 9 + i for r in range(9)])           # column
    for br in range(3):
        for bc in range(3):
            units.append([r * 9 + c
                          for r in range(br * 3, br * 3 + 3)
                          for c in range(bc * 3, bc * 3 + 3)])  # box
    if diagonals:
        units.append([i * 9 + i for i in range(9)])           # top-left to bottom-right
        units.append([i * 9 + (8 - i) for i in range(9)])     # top-right to bottom-left
    return np.array(units)


def fitness(population, units):
    """Distinct digits summed over every unit, for each individual.

    A perfect grid scores 9 per unit. The genes never see this number; it only
    decides their fate.

    Each digit d becomes the bit 1 << d; OR-ing a unit's bits and counting the
    ones gives the number of distinct digits in that unit.
    """
    bits = np.left_shift(np.int16(1), population.astype(np.int16))
    present = np.bitwise_or.reduce(bits[:, units], axis=2)
    return BIT_COUNT[present].sum(axis=1)


def conflict_cells(grid, units):
    """Cells whose digit is repeated in at least one of their units (display only)."""
    bad = np.zeros(CELLS, dtype=bool)
    for unit in units:
        values = grid[unit]
        counts = np.bincount(values, minlength=10)
        bad[unit] |= counts[values] > 1
    return bad


# --------------------------------------------------------------------------
# Blind variation: nothing here looks at the rules
# --------------------------------------------------------------------------

def random_genomes(count, rng):
    """Every gene is an independent random digit. Duplicates are allowed."""
    return rng.integers(1, 10, size=(count, CELLS), dtype=np.int8)


def build_world(side):
    """For every territory: itself and its 4 neighbours (north, south, east, west).

    The map wraps around, so every territory has the same number of neighbours.
    """
    row, col = np.divmod(np.arange(side * side), side)
    steps = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
    return np.stack([((row + dr) % side) * side + (col + dc) % side
                     for dr, dc in steps], axis=1)


def reproduce(mothers, fathers, crossover_rate, rng):
    """Build children chromosome by chromosome.

    For each of the 9 chromosomes a random cut point splits it: genes before the
    cut come from one parent, genes after it from the other, and which parent
    goes first is a coin flip. A cut at 0 or 9 passes the chromosome on whole.
    Children that are not born from crossover are copies of the mother.
    """
    n = len(mothers)
    cut = rng.integers(0, 10, size=(n, 9, 1))
    mother_first = rng.random((n, 9, 1)) < 0.5
    from_mother = (POSITIONS < cut) == mother_first
    from_mother |= rng.random((n, 1, 1)) >= crossover_rate
    children = np.where(from_mother, mothers.reshape(n, 9, 9), fathers.reshape(n, 9, 9))
    return children.reshape(n, CELLS)


def mutate(children, mutations, rng):
    """Overwrite random genes with new random digits. No swapping, no aiming."""
    n = len(children)
    who = np.repeat(np.arange(n), mutations)
    where = rng.integers(0, CELLS, size=n * mutations)
    children[who, where] = rng.integers(1, 10, size=n * mutations, dtype=np.int8)
    return children


# --------------------------------------------------------------------------
# Natural selection
# --------------------------------------------------------------------------

def choose_parents(neighbours, scores, rng, selection):
    """One parent for every territory, found among its neighbours.

    Two random neighbours meet and the fitter one gets to breed. With selection
    off, a random neighbour breeds.
    """
    n, k = neighbours.shape
    territory = np.arange(n)
    if not selection:
        return neighbours[territory, rng.integers(0, k, size=n)]
    contenders = neighbours[territory[:, None], rng.integers(0, k, size=(n, 2))]
    winner = scores[contenders].argmax(axis=1)
    return contenders[territory, winner]


def survive(population, scores, children, child_scores, selection):
    """Each newborn challenges the grid living in its territory.

    The newborn takes the territory if it is at least as fit; otherwise it dies
    and the resident stays. Nothing else is checked: copies of the same grid are
    free to fill as many territories as they can win. With selection off, every
    newborn replaces the resident.
    """
    wins = child_scores >= scores if selection else np.ones(len(scores), dtype=bool)
    population[wins] = children[wins]
    scores[wins] = child_scores[wins]
    return population, scores


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

GREEN, RED, BOLD, RESET = "\x1b[32m", "\x1b[31;1m", "\x1b[1m", "\x1b[0m"


def enable_ansi():
    """Turn on escape-code handling in the Windows console. Returns success."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def format_grid(grid, units, color, diagonals):
    """Green digits obey every rule, red digits break at least one."""
    bad = conflict_cells(grid, units)
    on_diagonal = {i * 9 + i for i in range(9)} | {i * 9 + 8 - i for i in range(9)}
    lines = []
    for r in range(9):
        if r in (3, 6):
            lines.append("  ------+-------+------")
        parts = []
        for c in range(9):
            i = r * 9 + c
            digit = str(grid[i])
            if color:
                style = RED if bad[i] else GREEN
                if diagonals and i in on_diagonal:
                    style += "\x1b[4m"
                cell = f"{style}{digit}{RESET}"
            else:
                cell = digit + ("*" if bad[i] else " ")
            parts.append(cell)
            if c in (2, 5):
                parts.append("|")
        sep = " " if color else ""
        lines.append("  " + sep.join(parts))
    return lines


def status_lines(generation, population_best, best_ever, max_score, scores,
                 genes_drawn, color):
    bold, reset = (BOLD, RESET) if color else ("", "")
    return [
        f"generation {bold}{generation:>6}{reset}   "
        f"best now {population_best}/{max_score}   best ever {bold}{best_ever}{reset}   "
        f"average {scores.mean():.1f}",
        f"random digits drawn {genes_drawn:,}   "
        f"rule breaks left {max_score - population_best}",
    ]


class LiveView:
    """Redraws the same block of lines in place."""

    def __init__(self, stream):
        self.stream = stream
        self.height = 0

    def draw(self, lines):
        out = []
        if self.height:
            out.append(f"\x1b[{self.height}F")
        out.extend(line + "\x1b[K\n" for line in lines)
        self.stream.write("".join(out))
        self.stream.flush()
        self.height = len(lines)


# --------------------------------------------------------------------------
# Evolution loop
# --------------------------------------------------------------------------

def evolve(args, rng, units, color, live):
    max_score = 9 * len(units)
    neighbours = build_world(args.world)
    n = len(neighbours)
    selection = not args.no_selection

    population = random_genomes(n, rng)
    scores = fitness(population, units)
    random_average = scores.mean()
    genes_drawn = n * CELLS
    judged = n

    best_index = scores.argmax()
    best_grid, best_score = population[best_index].copy(), int(scores[best_index])

    if not args.quiet:
        print(f"Generation 0: {n} grids of pure chance "
              f"(best {best_score}/{max_score}, average {random_average:.1f})")
        print("\n".join(format_grid(best_grid, units, color, args.diagonals)))
        print()

    view = LiveView(sys.stdout) if live else None
    generation = 0
    started = time.perf_counter()

    for generation in range(1, args.generations + 1):
        mothers = population[choose_parents(neighbours, scores, rng, selection)]
        fathers = population[choose_parents(neighbours, scores, rng, selection)]
        children = reproduce(mothers, fathers, args.crossover_rate, rng)
        mutate(children, args.mutations, rng)
        child_scores = fitness(children, units)
        genes_drawn += n * args.mutations
        judged += n

        population, scores = survive(population, scores, children, child_scores, selection)

        top = scores.argmax()
        if scores[top] > best_score:
            best_score = int(scores[top])
            best_grid = population[top].copy()

        done = best_score == max_score
        if not args.quiet and (done or generation % args.every == 0):
            status = status_lines(generation, int(scores.max()), best_score, max_score,
                                  scores, genes_drawn, color)
            if view:
                shown = population[scores.argmax()]
                view.draw(status + [""] + format_grid(shown, units, color, args.diagonals))
            elif done or generation % (args.every * 10) == 0:
                print("   ".join(status), flush=True)
        if done:
            break

    return {
        "grid": best_grid,
        "score": best_score,
        "max_score": max_score,
        "generations": generation,
        "seconds": time.perf_counter() - started,
        "genes_drawn": genes_drawn,
        "judged": judged,
        "random_average": random_average,
        "final_average": scores.mean(),
    }


def is_valid(grid, units):
    return all(sorted(grid[unit]) == list(range(1, 10)) for unit in units)


def report(result, args, units, color):
    grid = result["grid"]
    kind = "X-Sudoku" if args.diagonals else "Sudoku"
    print()
    print("Best grid found:")
    print("\n".join(format_grid(grid, units, color, args.diagonals)))
    print()

    chance = POSSIBLE_GRIDS // VALID_SUDOKU_GRIDS
    exponent = len(str(chance)) - 1

    if is_valid(grid, units):
        print(f"Valid {kind} grid in generation {result['generations']} "
              f"({result['seconds']:.1f} s).")
    else:
        print(f"No valid {kind} grid after {result['generations']} generations. "
              f"Best {result['score']}/{result['max_score']} "
              f"({result['max_score'] - result['score']} rule breaks left).")

    print()
    print("What happened:")
    print(f"  - every one of the {result['genes_drawn']:,} digits ever placed was drawn at random")
    print(f"  - the environment judged {result['judged']:,} grids; "
          f"it never edited one or told a gene where to go")
    print(f"  - the population's average score went from {result['random_average']:.1f} "
          f"(pure chance) to {result['final_average']:.1f} out of {result['max_score']}")
    print(f"  - pure chance makes a valid Sudoku less than once in 10^{exponent} grids")
    if args.no_selection:
        print("  - selection was OFF: random neighbours bred and every newborn took over,")
        print("    so the same randomness had nothing to keep and nothing to discard")
    else:
        print("  - the rules live only in the fitness score; selection did the rest")
    return 0 if is_valid(grid, units) else 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def bounded_int(minimum):
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}")
        if number < minimum:
            raise argparse.ArgumentTypeError(f"must be at least {minimum}, got {number}")
        return number
    return parse


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evolve a valid Sudoku grid from random digits by natural selection.")
    parser.add_argument("-g", "--generations", type=bounded_int(1), default=50000,
                        help="maximum number of generations (default: 50000)")
    parser.add_argument("-w", "--world", type=bounded_int(3), default=120,
                        help="side of the square world map; population is side x side "
                             "(default: 120, i.e. 14400 grids)")
    parser.add_argument("-x", "--diagonals", action="store_true",
                        help="add the corner-to-corner rule: both diagonals hold 1..9 (X-Sudoku)")
    parser.add_argument("-m", "--mutations", type=bounded_int(0), default=1,
                        help="random genes redrawn in every child (default: 1)")
    parser.add_argument("-c", "--crossover-rate", type=float, default=0.2,
                        help="chance a child has two parents instead of one (default: 0.2)")
    parser.add_argument("--no-selection", action="store_true",
                        help="control experiment: ignore fitness when choosing parents "
                             "and survivors")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="seed for a reproducible run (default: fresh OS entropy)")
    parser.add_argument("--every", type=bounded_int(1), default=10,
                        help="redraw the display every N generations (default: 10)")
    parser.add_argument("--no-live", action="store_true",
                        help="print progress lines instead of redrawing the grid")
    parser.add_argument("--no-color", action="store_true",
                        help="mark broken cells with * instead of colors")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="only print the final result")
    args = parser.parse_args(argv)

    if not 0.0 <= args.crossover_rate <= 1.0:
        parser.error("--crossover-rate must be between 0 and 1")

    interactive = sys.stdout.isatty()
    ansi = interactive and enable_ansi()
    color = ansi and not args.no_color
    live = ansi and not args.no_live

    seed = args.seed if args.seed is not None else secrets.randbits(63)
    rng = np.random.default_rng(seed)
    units = build_units(args.diagonals)

    if not args.quiet:
        rules = "rows, columns, boxes" + (" and both diagonals" if args.diagonals else "")
        print(f"Rules known only to the environment: {rules}.")
        print(f"World {args.world}x{args.world} ({args.world ** 2} grids), "
              f"up to {args.generations} generations, "
              f"selection {'OFF' if args.no_selection else 'on'}, seed {seed}.")
        print()

    result = evolve(args, rng, units, color, live)
    return report(result, args, units, color)


if __name__ == "__main__":
    sys.exit(main())
