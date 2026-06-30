"""Reusable maze generation module using recursive backtracker algorithm.

Example usage::

    from mazegen import MazeGenerator

    gen = MazeGenerator(width=20, height=15, seed=42, perfect=True)
    gen.generate()
    print(gen.grid)          # 2D list of wall-bit integers
    print(gen.solution)      # list of 'N'/'E'/'S'/'W' moves
    print(gen.entry)         # (col, row)
    print(gen.exit_cell)     # (col, row)
"""

import random
from collections import deque
from typing import Optional

# Wall bit masks
NORTH: int = 1 << 0
EAST: int = 1 << 1
SOUTH: int = 1 << 2
WEST: int = 1 << 3
ALL_WALLS: int = NORTH | EAST | SOUTH | WEST

# Opposite wall for each direction
OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    SOUTH: NORTH,
    EAST: WEST,
    WEST: EAST,
}

# Movement deltas (col, row) for each direction
DELTA: dict[int, tuple[int, int]] = {
    NORTH: (0, -1),
    EAST: (1, 0),
    SOUTH: (0, 1),
    WEST: (-1, 0),
}

DIR_LETTER: dict[int, str] = {
    NORTH: "N",
    EAST: "E",
    SOUTH: "S",
    WEST: "W",
}

# Pixel patterns for digits '4' and '2' on a 5-row x 3-col grid
_DIGIT_4: list[list[int]] = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]

_DIGIT_2: list[list[int]] = [
    [1, 1, 1],
    [0, 0, 1],
    [1, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]

# "42" occupies 5 rows x 7 cols (3+1gap+3)
_PATTERN_ROWS: int = 5
_PATTERN_COLS: int = 7  # 3 + 1 gap + 3
_MIN_WIDTH: int = _PATTERN_COLS + 4   # 2-cell border on each side
_MIN_HEIGHT: int = _PATTERN_ROWS + 4


def _build_42_mask(offset_col: int, offset_row: int) -> set[tuple[int, int]]:
    """Return the set of (col, row) cells that form the '42' closed-cell pattern."""
    cells: set[tuple[int, int]] = set()
    for r, row in enumerate(_DIGIT_4):
        for c, val in enumerate(row):
            if val:
                cells.add((offset_col + c, offset_row + r))
    for r, row in enumerate(_DIGIT_2):
        for c, val in enumerate(row):
            if val:
                cells.add((offset_col + 4 + c, offset_row + r))
    return cells


class MazeGenerator:
    """Generate a maze using the recursive backtracker (DFS) algorithm.

    Args:
        width: Number of cells horizontally.
        height: Number of cells vertically.
        entry: (col, row) of the entry cell.
        exit_cell: (col, row) of the exit cell.
        seed: Random seed for reproducibility.
        perfect: If True, generate a perfect maze (exactly one path between any two cells).
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int] = (0, 0),
        exit_cell: Optional[tuple[int, int]] = None,
        seed: Optional[int] = None,
        perfect: bool = True,
    ) -> None:
        """Initialize the maze generator with dimensions and options."""
        if width < 2 or height < 2:
            raise ValueError("Maze must be at least 2x2 cells.")
        self.width = width
        self.height = height
        self.entry = entry
        self.exit_cell = exit_cell if exit_cell is not None else (width - 1, height - 1)
        self.seed = seed
        self.perfect = perfect

        # grid[row][col] = bitmask of CLOSED walls (1=closed)
        self.grid: list[list[int]] = [[ALL_WALLS] * width for _ in range(height)]
        self.solution: list[str] = []
        self._forty_two_cells: set[tuple[int, int]] = set()
        self._has_pattern: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Generate the maze. Populates self.grid and self.solution."""
        rng = random.Random(self.seed)
        self._reset()
        self._place_42_pattern()
        self._carve_passages(rng)
        if not self.perfect:
            self._add_extra_passages(rng)
        self._open_border_walls()
        self._enforce_border_walls()
        self.solution = self._bfs_solution()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Reset grid to all walls closed."""
        self.grid = [[ALL_WALLS] * self.width for _ in range(self.height)]

    def _place_42_pattern(self) -> None:
        """Mark cells that form the '42' as blocked (kept fully walled)."""
        if self.width < _MIN_WIDTH or self.height < _MIN_HEIGHT:
            self._has_pattern = False
            self._forty_two_cells = set()
            return
        self._has_pattern = True
        offset_col = (self.width - _PATTERN_COLS) // 2
        offset_row = (self.height - _PATTERN_ROWS) // 2
        self._forty_two_cells = _build_42_mask(offset_col, offset_row)

    def _is_blocked(self, col: int, row: int) -> bool:
        """Return True if this cell is part of the '42' pattern."""
        return (col, row) in self._forty_two_cells

    def _in_bounds(self, col: int, row: int) -> bool:
        """Return True if (col, row) is within the maze."""
        return 0 <= col < self.width and 0 <= row < self.height

    def _carve_passages(self, rng: random.Random) -> None:
        """Recursive backtracker: carve passages through the maze via iterative DFS."""
        visited: list[list[bool]] = [
            [self._is_blocked(c, r) for c in range(self.width)]
            for r in range(self.height)
        ]

        # Find a valid start cell (entry or first non-blocked)
        start_col, start_row = self.entry
        if self._is_blocked(start_col, start_row):
            start_col, start_row = self._find_unblocked_start(visited)

        visited[start_row][start_col] = True
        stack: list[tuple[int, int]] = [(start_col, start_row)]

        while stack:
            col, row = stack[-1]
            directions = list(DELTA.keys())
            rng.shuffle(directions)
            moved = False
            for direction in directions:
                dc, dr = DELTA[direction]
                nc, nr = col + dc, row + dr
                if self._in_bounds(nc, nr) and not visited[nr][nc]:
                    self._remove_wall(col, row, nc, nr, direction)
                    visited[nr][nc] = True
                    stack.append((nc, nr))
                    moved = True
                    break
            if not moved:
                stack.pop()

        # Ensure all non-blocked cells are reachable (connect isolated regions)
        self._connect_isolated(visited, rng)

    def _find_unblocked_start(self, visited: list[list[bool]]) -> tuple[int, int]:
        """Find the first cell that is not blocked."""
        for r in range(self.height):
            for c in range(self.width):
                if not visited[r][c]:
                    return c, r
        raise RuntimeError("All cells are blocked — maze too small for the 42 pattern.")

    def _connect_isolated(
        self, visited: list[list[bool]], rng: random.Random
    ) -> None:
        """Connect any cells not reached by the initial DFS (e.g., around '42' borders)."""
        for r in range(self.height):
            for c in range(self.width):
                if not visited[r][c] and not self._is_blocked(c, r):
                    # Find a visited neighbour and carve a wall
                    directions = list(DELTA.keys())
                    rng.shuffle(directions)
                    for direction in directions:
                        dc, dr = DELTA[direction]
                        nc, nr = c + dc, r + dr
                        if self._in_bounds(nc, nr) and visited[nr][nc]:
                            self._remove_wall(c, r, nc, nr, direction)
                            visited[r][c] = True
                            # BFS/DFS from this new cell
                            stack = [(c, r)]
                            while stack:
                                sc, sr = stack.pop()
                                for d2 in DELTA:
                                    dc2, dr2 = DELTA[d2]
                                    nc2, nr2 = sc + dc2, sr + dr2
                                    if (
                                        self._in_bounds(nc2, nr2)
                                        and not visited[nr2][nc2]
                                        and not self._is_blocked(nc2, nr2)
                                    ):
                                        self._remove_wall(sc, sr, nc2, nr2, d2)
                                        visited[nr2][nc2] = True
                                        stack.append((nc2, nr2))
                            break

    def _remove_wall(
        self, col: int, row: int, ncol: int, nrow: int, direction: int
    ) -> None:
        """Remove the wall between (col, row) and its neighbour in direction."""
        self.grid[row][col] &= ~direction
        self.grid[nrow][ncol] &= ~OPPOSITE[direction]

    def _add_extra_passages(self, rng: random.Random) -> None:
        """Add a few extra passages to create loops (imperfect maze)."""
        extra = max(1, (self.width * self.height) // 20)
        for _ in range(extra):
            col = rng.randint(0, self.width - 2)
            row = rng.randint(0, self.height - 1)
            if not self._is_blocked(col, row) and not self._is_blocked(col + 1, row):
                self._remove_wall(col, row, col + 1, row, EAST)

    def _open_border_walls(self) -> None:
        """Open the outer border wall at entry and exit cells."""
        ec, er = self.entry
        xc, xr = self.exit_cell
        # Entry: open whichever border face the cell is on
        if er == 0:
            self.grid[er][ec] &= ~NORTH
        elif er == self.height - 1:
            self.grid[er][ec] &= ~SOUTH
        elif ec == 0:
            self.grid[er][ec] &= ~WEST
        else:
            self.grid[er][ec] &= ~EAST

        # Exit
        if xr == 0:
            self.grid[xr][xc] &= ~NORTH
        elif xr == self.height - 1:
            self.grid[xr][xc] &= ~SOUTH
        elif xc == 0:
            self.grid[xr][xc] &= ~WEST
        else:
            self.grid[xr][xc] &= ~EAST

    def _enforce_border_walls(self) -> None:
        """Close all outer border walls except at entry/exit openings."""
        ec, er = self.entry
        xc, xr = self.exit_cell

        for c in range(self.width):
            # Top border
            if not (c == ec and er == 0) and not (c == xc and xr == 0):
                self.grid[0][c] |= NORTH
            # Bottom border
            if not (c == ec and er == self.height - 1) and not (
                c == xc and xr == self.height - 1
            ):
                self.grid[self.height - 1][c] |= SOUTH

        for r in range(self.height):
            # Left border
            if not (r == er and ec == 0) and not (r == xr and xc == 0):
                self.grid[r][0] |= WEST
            # Right border
            if not (r == er and ec == self.width - 1) and not (
                r == xr and xc == self.width - 1
            ):
                self.grid[r][self.width - 1] |= EAST

    def _bfs_solution(self) -> list[str]:
        """Return shortest path from entry to exit as a list of direction letters."""
        start = self.entry
        goal = self.exit_cell
        if start == goal:
            return []

        queue: deque[tuple[tuple[int, int], list[str]]] = deque()
        queue.append((start, []))
        visited: set[tuple[int, int]] = {start}

        while queue:
            (col, row), path = queue.popleft()
            for direction, (dc, dr) in DELTA.items():
                nc, nr = col + dc, row + dr
                if not self._in_bounds(nc, nr):
                    continue
                if (nc, nr) in visited:
                    continue
                if self.grid[row][col] & direction:
                    # Wall is closed — can't pass
                    continue
                new_path = path + [DIR_LETTER[direction]]
                if (nc, nr) == goal:
                    return new_path
                visited.add((nc, nr))
                queue.append(((nc, nr), new_path))
        return []  # No path found (shouldn't happen in a valid maze)

    @property
    def forty_two_cells(self) -> set[tuple[int, int]]:
        """Return the set of cells forming the '42' pattern."""
        return self._forty_two_cells

    @property
    def has_pattern(self) -> bool:
        """Return True if the '42' pattern was embedded in the maze."""
        return self._has_pattern
