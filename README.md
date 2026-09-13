# Darwin's Sudoku

**Can random chance plus natural selection build something complex?**
This project answers with an experiment you can run in a few seconds: thousands of Sudoku grids start as random numbers, know nothing about the rules, and still evolve into a perfect Sudoku, but only when nature is allowed to choose who survives.

📖 **Read the article:** [ali1995reza.github.io/darwin-sudoku](https://ali1995reza.github.io/darwin-sudoku/). It's an interactive, plain-language write-up in **English and Farsi**, with light and dark themes, charts and a replay of a real run. The source is [`article.html`](article.html).

---

## Why this project exists

A common belief is that evolution means "everything happened by chance". Chance alone really could never build something complex, and this project shows exactly how impossible that would be.

Darwin described something different, with two parts:

1. **Random changes** happen all the time.
2. **Nature keeps what works** and removes what doesn't.

> The changes are random. The choosing is not.

This program makes that difference visible and measurable. It runs the same randomness with and without selection and compares both to pure luck.

## The experiment in short

| Test | What happens | Result (same number of grids checked) |
|---|---|---|
| **Pure luck** | Make random grids, one after another | Best of 8,092,800 grids: 189/243, never valid |
| **Nobody chooses** | Parents, children and random changes, but no selection | Average score stays at 159, never valid |
| **Nature chooses** | Same randomness, plus selection | ✅ Perfect Sudoku in generation 561 (about 6 seconds) |

The last test was repeated with 16 different random seeds, and **all 16 produced a valid Sudoku** (between generation 258 and 1,339).

How unlikely is pure luck? A random grid is a valid Sudoku about **once in 2.9 × 10^55 tries**. Checking 1.4 million grids per second, a laptop would need roughly 4.9 × 10^31 times the age of the universe.

## How it works

Each Sudoku grid is a little creature:

- **Genes:** its 81 numbers, arranged as 9 rows ("chromosomes").
- **Birth:** every number is random, from 1 to 9. Duplicates are allowed; nothing blocks them.
- **No knowledge:** a number doesn't know where it is, what its neighbours are, or that rules exist.

The rules exist in one place only, **the environment**. It gives every grid a score: the number of distinct digits in every row, column and 3×3 box. A perfect grid scores **243** (27 groups × 9). The environment never edits a grid or says what to change; it only decides who survives.

### One generation

14,400 grids live on a 120 × 120 world map that wraps around at the edges, one grid per territory. In every territory, each generation:

1. **Parents:** two random neighbours meet; the one with the higher score gets to breed (this happens twice, for a mother and a father).
2. **Child:** usually a copy of the mother. 20% of the time, each row is cut at a random point and mixed from both parents.
3. **Mutation:** one random cell gets a new random digit. It isn't aimed, and it can even draw the same digit.
4. **Survival:** the child takes the territory if it scores at least as well as the grid living there. Otherwise it dies.

Identical copies of a grid are allowed. Because a good grid can only spread one territory at a time, distant regions keep exploring different solutions, as real populations on different islands or in different valleys do.

## Getting started

### Requirements

- Python 3
- [NumPy](https://numpy.org/)

Tested with Python 3.14 and NumPy 2.5.

### Install

```bash
git clone https://github.com/ali1995reza/darwin-sudoku.git
cd darwin-sudoku
pip install numpy
```

### Run

```bash
# random changes + natural selection
python sudoku.py

# the control experiment: same randomness, nobody chooses
python sudoku.py --no-selection -g 561

# a harder environment: both diagonals must also hold 1 to 9
python sudoku.py --diagonals

# repeat the exact run used in the article
python sudoku.py --seed 7
```

In a terminal that supports colors, the best grid is redrawn live: green digits follow every rule, red digits break at least one. Without color support, broken cells are marked with `*`.

### Example output

```text
Rules known only to the environment: rows, columns, boxes.
World 120x120 (14400 grids), up to 50000 generations, selection on, seed 7.

Generation 0: 14400 grids of pure chance (best 180/243, average 158.8)
  1*1*4*|8*3*9 |3*7 4*
  6*8*2*|5*8*2*|2*9 8*
  2*3*8*|1*6*5*|6*1*4*
  ------+-------+------
  ...

Best grid found:
  1 7 9 |4 6 2 |3 5 8
  8 3 6 |7 1 5 |9 4 2
  2 4 5 |9 3 8 |7 1 6
  ------+-------+------
  6 2 7 |1 5 9 |4 8 3
  5 8 3 |2 7 4 |1 6 9
  9 1 4 |6 8 3 |5 2 7
  ------+-------+------
  3 9 2 |5 4 6 |8 7 1
  4 6 1 |8 9 7 |2 3 5
  7 5 8 |3 2 1 |6 9 4

Valid Sudoku grid in generation 561 (6.1 s).

What happened:
  - every one of the 9,244,800 digits ever placed was drawn at random
  - the environment judged 8,092,800 grids; it never edited one or told a gene where to go
  - the population's average score went from 158.8 (pure chance) to 239.5 out of 243
  - pure chance makes a valid Sudoku less than once in 10^55 grids
  - the rules live only in the fitness score; selection did the rest
```

## Options

| Option | Default | Description |
|---|---|---|
| `-g`, `--generations` | `50000` | Maximum number of generations |
| `-w`, `--world` | `120` | Side of the square world map; the population is side × side (14,400 grids) |
| `-x`, `--diagonals` | off | Add the corner-to-corner rule (X-Sudoku, max score 261) |
| `-m`, `--mutations` | `1` | Random genes redrawn in every child |
| `-c`, `--crossover-rate` | `0.2` | Chance a child has two parents instead of one |
| `--no-selection` | off | Control experiment: ignore scores when choosing parents and survivors |
| `-s`, `--seed` | random | Seed for a reproducible run (otherwise fresh randomness from the operating system) |
| `--every` | `10` | Redraw the display every N generations |
| `--no-live` | off | Print progress lines instead of redrawing the grid |
| `--no-color` | off | Mark broken cells with `*` instead of colors |
| `-q`, `--quiet` | off | Only print the final result |

The program exits with code `0` when it finds a valid grid and `1` when it doesn't.

## What's random and what isn't

| Part | Random? | Uses the Sudoku rules? |
|---|---|---|
| First generation | ✅ every digit random | ❌ |
| Mutation | ✅ random cell, random digit | ❌ |
| Crossover | ✅ random cut points | ❌ |
| Choosing parents | Partly: random neighbours meet, the fitter one breeds | Only through the score |
| Survival | No: the fitter grid keeps the territory | Only through the score |

Selection is the only part that isn't random, and that's the point. Switch it off with `--no-selection`, and the same randomness goes nowhere.

## Limits

**The diagonal puzzle usually gets stuck.** With `--diagonals`, evolution typically reaches 258–260 out of 261 and stops (0 of 16 runs finished within 4,000 generations). Once a grid follows every row, column and box rule, fixing a diagonal needs about four numbers to change at the same time. Changing any one of them first makes the grid worse, so that child dies. Biologists call this a *fitness valley*: complex features evolve when each small step along the way is useful on its own.

**This is a demonstration, not a proof.** The program shows that the *mechanism* works: random variation plus selection builds complex order, while randomness alone does not. The evidence that life actually evolved this way comes from biology: observed evolution (for example antibiotic resistance), fossils, and DNA.

## Project structure

```text
.
├── sudoku.py      # the evolution experiment (command-line program)
├── article.html   # interactive article explaining the experiment and results
├── index.html     # redirects the GitHub Pages site to the article
├── README.md
├── LICENSE
└── .gitignore
```

## Background and references

- Charles Darwin, *On the Origin of Species* (1859)
- Bertram Felgenhauer and Frazer Jarvis (2005), "Enumerating possible Sudoku grids": there are 6,670,903,752,021,072,936,960 valid 9×9 Sudoku grids
- Richard Lenski et al. (2003), "The evolutionary origin of complex features", *Nature*: digital organisms evolve complex functions only when simpler intermediate steps are rewarded

## License

This project is licensed under the [MIT License](LICENSE). You're free to use, copy, modify and share it, as long as the copyright notice is kept.
