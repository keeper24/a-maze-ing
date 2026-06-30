*This project has been created as part of the 42 curriculum by mekaraca, msoytas.*

# A-Maze-ing

## Description

A-Maze-ing is a maze generator written in Python 3. It reads a configuration file, generates a maze using the **recursive backtracker (DFS)** algorithm, writes the result to a hex-encoded output file, and renders the maze interactively in the terminal using ASCII box-drawing characters. Every generated maze embeds a visible **"42"** pattern formed by fully-walled cells placed at the center of the grid.

## Instructions

### Requirements

- Python 3.10+
- `flake8` and `mypy` (for linting)
- `build` (for packaging)

### Install dependencies

```bash
make install
```

### Run

```bash
make run
# or directly:
python3 a_maze_ing.py config.txt
```

### Debug

```bash
make debug
```

### Lint

```bash
make lint
```

### Build the reusable package

```bash
make build-pkg
# Produces dist/mazegen-1.0.0-py3-none-any.whl and dist/mazegen-1.0.0.tar.gz
```

### Install the package in a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install dist/mazegen-1.0.0-py3-none-any.whl
```

---

## Configuration file format

The config file uses one `KEY=VALUE` pair per line. Lines starting with `#` are ignored.

| Key | Description | Example |
|---|---|---|
| `WIDTH` | Number of cells horizontally | `WIDTH=20` |
| `HEIGHT` | Number of cells vertically | `HEIGHT=15` |
| `ENTRY` | Entry cell as `x,y` (col,row) | `ENTRY=0,0` |
| `EXIT` | Exit cell as `x,y` | `EXIT=19,14` |
| `OUTPUT_FILE` | Path to write the hex output | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | `True` for perfect maze, `False` for loops | `PERFECT=True` |
| `SEED` | *(optional)* Integer seed for reproducibility | `SEED=42` |

---

## Maze generation algorithm

**Recursive Backtracker (Iterative DFS)**

Starting from the entry cell, the algorithm:
1. Marks the current cell as visited.
2. Picks a random unvisited neighbour and carves a passage to it.
3. Pushes the new cell onto a stack and repeats.
4. When no unvisited neighbours remain, backtracks via the stack.

This produces mazes with long, winding corridors and relatively few dead ends — perfect for a single-path (perfect) maze.

**Why this algorithm?**  
It is simple to implement iteratively, produces visually interesting mazes, and maps directly to spanning trees (perfect maze = spanning tree of the cell graph). The "42" pattern cells are simply skipped during carving: they remain fully walled, and the surrounding cells are connected around them.

---

## Output file format

```
<hex row 0>
<hex row 1>
...
<hex row N-1>

<entry_col>,<entry_row>
<exit_col>,<exit_row>
<path as N/E/S/W letters>
```

Each hex digit encodes which walls are **closed** (bit=1) using:

| Bit | Direction |
|---|---|
| 0 (LSB) | North |
| 1 | East |
| 2 | South |
| 3 | West |

Example: `3` = `0011` = North and East walls closed.

---

## Reusable module (`mazegen`)

The `MazeGenerator` class in `mazegen.py` is a standalone module publishable as a pip package.

### Quickstart

```python
from mazegen import MazeGenerator

gen = MazeGenerator(
    width=20,
    height=15,
    entry=(0, 0),
    exit_cell=(19, 14),
    seed=42,
    perfect=True,
)
gen.generate()

# Access results
print(gen.grid)          # list[list[int]] — wall bitmask per cell
print(gen.solution)      # list[str] — e.g. ['E', 'S', 'E', ...]
print(gen.entry)         # (col, row)
print(gen.exit_cell)     # (col, row)
print(gen.forty_two_cells)  # set of (col, row) forming the '42' pattern
print(gen.has_pattern)   # True if maze was large enough for the pattern
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `width` | `int` | Maze width in cells (≥2) |
| `height` | `int` | Maze height in cells (≥2) |
| `entry` | `tuple[int,int]` | Entry cell `(col, row)`, default `(0,0)` |
| `exit_cell` | `tuple[int,int]` | Exit cell, default bottom-right |
| `seed` | `int \| None` | Random seed; `None` = non-reproducible |
| `perfect` | `bool` | `True` = perfect maze (single path) |

---

## Team and project management

**Team members:**
- **Melik Karaca** (mekaraca) — maze engine, hex output, packaging
- **Miraç Soytaş** (msoytas) — ASCII renderer, config parser, Makefile, README

**Planning:**
- Phase 1: Core `MazeGenerator` class with recursive backtracker and "42" pattern
- Phase 2: Config parser, hex output writer, interactive ASCII display
- Phase 3: Packaging (`pyproject.toml`), project files, README

**What worked well:**
- The iterative DFS was straightforward to implement and debug.
- The wall bitmask representation made the hex output format trivial.
- ASCII box-drawing characters produced a clean visual with minimal code.

**What could be improved:**
- A `curses`-based display would allow real-time interaction without screen-clearing.
- Supporting multiple algorithms (Prim's, Kruskal's) as a bonus would be educational.

**Tools used:**
- Python 3 stdlib only (no external runtime dependencies).
- `flake8` and `mypy` for code quality.
- `build` for packaging.
- AI (Claude) used to: review algorithm correctness, suggest box-drawing junction logic, draft README structure. All generated code was reviewed and understood by team members.

---

## Resources

- [Maze generation algorithms — Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Recursive backtracker — Jamis Buck's blog](https://weblog.jamisbuck.org/2010/12/27/maze-generation-recursive-backtracker)
- [Spanning trees and perfect mazes — theory](https://en.wikipedia.org/wiki/Maze_solving_algorithm)
- [Python `random` module](https://docs.python.org/3/library/random.html)
- [Unicode box-drawing characters](https://en.wikipedia.org/wiki/Box-drawing_characters)
- **AI usage:** Claude (Anthropic) was used to review the junction-character rendering logic and suggest the BFS solution approach. All code was written, read, and understood by the team.
