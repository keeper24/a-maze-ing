"""A-Maze-ing: maze generator entry point.

Usage::

    python3 a_maze_ing.py config.txt
"""

import random
import sys
import os
from typing import Optional
from mazegen import (
    MazeGenerator,
    MIN_WIDTH,
    MIN_HEIGHT,
    NORTH,
    EAST,
    SOUTH,
    WEST,
    DELTA,
)

# Configuration
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_KEYS: list[str] = [
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"
]


def parse_config(path: str) -> dict[str, str]:
    """Parse a KEY=VALUE config file, ignoring comment lines.

    Args:
        path: Path to the config file.

    Returns:
        Dictionary of key→value strings.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If a line has invalid syntax or a required key is missing.
    """
    config: dict[str, str] = {}
    try:
        with open(path, "r") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(
                        f"Config line {lineno}: expected KEY=VALUE, "
                        f"got: {line!r}"
                    )
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path!r}")

    missing = [k for k in REQUIRED_KEYS if k not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    return config


def build_generator(config: dict[str, str]) -> tuple[MazeGenerator, str]:
    """Validate config values and return a MazeGenerator and output path.

    Args:
        config: Parsed config dictionary.

    Returns:
        Tuple of (MazeGenerator instance, output file path).

    Raises:
        ValueError: On invalid config values.
    """
    try:
        width = int(config["WIDTH"])
        height = int(config["HEIGHT"])
    except ValueError:
        raise ValueError("WIDTH and HEIGHT must be integers.")

    if width < 2 or height < 2:
        raise ValueError("WIDTH and HEIGHT must each be at least 2.")

    def parse_coord(raw: str, key: str) -> tuple[int, int]:
        """Parse 'x,y' string into (col, row) integers."""
        parts = raw.split(",")
        if len(parts) != 2:
            raise ValueError(f"{key} must be in 'x,y' format, got: {raw!r}")
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"{key} coordinates must be integers, got: {raw!r}"
            )

    entry = parse_coord(config["ENTRY"], "ENTRY")
    exit_cell = parse_coord(config["EXIT"], "EXIT")

    for label, (c, r) in [("ENTRY", entry), ("EXIT", exit_cell)]:
        if not (0 <= c < width and 0 <= r < height):
            raise ValueError(
                f"{label} ({c},{r}) is outside maze bounds ({width}x{height})."
            )

    if entry == exit_cell:
        raise ValueError("ENTRY and EXIT must be different cells.")

    perfect_raw = config["PERFECT"].strip().lower()
    if perfect_raw not in ("true", "false"):
        raise ValueError("PERFECT must be 'True' or 'False'.")
    perfect = perfect_raw == "true"

    seed: Optional[int] = None
    if "SEED" in config:
        try:
            seed = int(config["SEED"])
        except ValueError:
            raise ValueError("SEED must be an integer.")

    output_file = config["OUTPUT_FILE"].strip()
    if not output_file:
        raise ValueError("OUTPUT_FILE must not be empty.")

    gen = MazeGenerator(
        width=width,
        height=height,
        entry=entry,
        exit_cell=exit_cell,
        seed=seed,
        perfect=perfect,
    )
    return gen, output_file


# Hex output
# ──────────────────────────────────────────────────────────────────────────────

def write_output(gen: MazeGenerator, output_file: str) -> None:
    """Write the maze to a file in hex-per-cell format.

    Format:
        - One row per line, each cell as a single hex digit (wall bitmask).
        - A blank line separates the grid from the footer.
        - Footer: entry coords, exit coords, solution path.

    Args:
        gen: A MazeGenerator that has already run generate().
        output_file: Destination file path.
    """
    ec, er = gen.entry
    xc, xr = gen.exit_cell
    path_str = "".join(gen.solution)

    with open(output_file, "w") as f:
        for row in gen.grid:
            f.write("".join(format(cell, "X") for cell in row) + "\n")
        f.write("\n")
        f.write(f"{ec},{er}\n")
        f.write(f"{xc},{xr}\n")
        f.write(path_str + "\n")


# ASCII renderer
# ──────────────────────────────────────────────────────────────────────────────

# Box-drawing character lookup:
# Key = (has_south, has_east, has_north, has_west) as booleans
# We build junction chars for the top-left corner of each cell.

_VERT = "│"
_HORIZ = "─"
_JUNCTIONS: dict[tuple[bool, bool, bool, bool], str] = {
    # (S, E, N, W)
    (False, False, False, False): " ",
    (True, False, False, False): "╵",
    (False, True, False, False): "╶",
    (False, False, True, False): "╷",
    (False, False, False, True): "╴",
    (True, True, False, False): "└",
    (True, False, True, False): "│",
    (True, False, False, True): "┘",
    (False, True, True, False): "┌",
    (False, True, False, True): "─",
    (False, False, True, True): "┐",
    (True, True, True, False): "├",
    (True, True, False, True): "┴",
    (True, False, True, True): "┤",
    (False, True, True, True): "┬",
    (True, True, True, True): "┼",
}


def _junction(grid: list[list[int]], r: int, c: int) -> str:
    """Return the junction character at grid corner (r, c).

    Corner (r, c) is between cells (r-1,c-1), (r-1,c), (r,c-1), (r,c).
    """
    height = len(grid)
    width = len(grid[0])

    def wall(row: int, col: int, direction: int) -> bool:
        """Return True if cell (row, col) has the given wall closed."""
        if 0 <= row < height and 0 <= col < width:
            return bool(grid[row][col] & direction)
        return True  # Out-of-bounds = outer wall

    # From this corner's perspective:
    # Going south  → right wall of cell (r-1, c-1) = EAST of (r-1, c-1)
    #                or WEST of (r-1, c)
    # Going east   → bottom wall of cell (r-1, c)   = SOUTH of (r-1, c)
    #                or NORTH of (r, c)
    # Going north  → right wall of cell (r, c-1)    = EAST of (r, c-1)
    #                or WEST of (r, c)
    # Going west   → bottom wall of cell (r, c-1)   = SOUTH of (r-1, c-1)
    #                or NORTH of (r, c-1)

    has_s = wall(r - 1, c - 1, EAST) or wall(r - 1, c, WEST)
    has_e = wall(r - 1, c, SOUTH) or wall(r, c, NORTH)
    has_n = wall(r, c - 1, EAST) or wall(r, c, WEST)
    has_w = wall(r - 1, c - 1, SOUTH) or wall(r, c - 1, NORTH)

    return _JUNCTIONS.get((has_s, has_e, has_n, has_w), "+")


# Colour schemes
# ──────────────────────────────────────────────────────────────────────────────

_RESET: str = "\033[0m"


class ColorScheme:
    """ANSI colour scheme for maze rendering."""

    def __init__(
        self, name: str, wall: str, path: str, entry: str, exit_c: str
    ) -> None:
        """Initialise with ANSI escape codes for each element."""
        self.name = name
        self.wall = wall
        self.path = path
        self.entry = entry
        self.exit_c = exit_c


COLOR_SCHEMES: list[ColorScheme] = [
    ColorScheme("Default", "",         "",         "",         ""),
    ColorScheme("Green",   "\033[32m", "\033[36m", "\033[95m", "\033[91m"),
    ColorScheme("Yellow",  "\033[33m", "\033[36m", "\033[95m", "\033[91m"),
    ColorScheme("Cyan",    "\033[96m", "\033[33m", "\033[95m", "\033[91m"),
    ColorScheme("Blue",    "\033[34m", "\033[36m", "\033[95m", "\033[91m"),
]


def _col(text: str, code: str) -> str:
    """Wrap text with ANSI colour code; unchanged if code is empty."""
    return text if not code else f"{code}{text}{_RESET}"


def render_maze(
    gen: MazeGenerator,
    show_path: bool = False,
    show_42: bool = True,
    scheme: Optional[ColorScheme] = None,
) -> str:
    """Render the maze as a multi-line ASCII string.

    Args:
        gen: A MazeGenerator that has already run generate().
        show_path: If True, overlay the solution path with '*'.
        show_42: If True, shade the '42' cells with '#'.
        scheme: Colour scheme for ANSI terminal output.

    Returns:
        String ready to print to the terminal.
    """
    active = scheme if scheme is not None else COLOR_SCHEMES[0]
    grid = gen.grid
    height = gen.height
    width = gen.width
    ec, er = gen.entry
    xc, xr = gen.exit_cell

    path_cells: set[tuple[int, int]] = set()
    if show_path and gen.solution:
        col, row = gen.entry
        path_cells.add((col, row))
        dir_map = {"N": NORTH, "E": EAST, "S": SOUTH, "W": WEST}
        for letter in gen.solution:
            dc, dr = DELTA[dir_map[letter]]
            col += dc
            row += dr
            path_cells.add((col, row))

    lines: list[str] = []

    for r in range(height + 1):
        line_top = ""
        line_mid = ""

        for c in range(width + 1):
            jchar = _junction(grid, r, c)
            line_top += _col(jchar, active.wall) if jchar != " " else " "

            if c < width:
                if r < height:
                    has_top = bool(grid[r][c] & NORTH)
                else:
                    has_top = bool(grid[r - 1][c] & SOUTH)
                if has_top:
                    line_top += _col(_HORIZ + _HORIZ, active.wall)
                else:
                    line_top += "  "

        lines.append(line_top)

        if r < height:
            for c in range(width + 1):
                if c < width:
                    has_left = bool(grid[r][c] & WEST)
                else:
                    has_left = bool(grid[r][c - 1] & EAST)
                line_mid += (
                    _col(_VERT, active.wall) if has_left else " "
                )

                if c < width:
                    if (c, r) == (ec, er):
                        interior = _col("S ", active.entry)
                    elif (c, r) == (xc, xr):
                        interior = _col("E ", active.exit_c)
                    elif show_42 and (c, r) in gen.forty_two_cells:
                        interior = "##"
                    elif show_path and (c, r) in path_cells:
                        interior = _col("* ", active.path)
                    else:
                        interior = "  "
                    line_mid += interior

            lines.append(line_mid)

    return "\n".join(lines)


# Interactive display loop
# ──────────────────────────────────────────────────────────────────────────────

def _clear() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def display_loop(
    gen: MazeGenerator, config: dict[str, str], output_file: str
) -> None:
    """Interactive loop: display maze and respond to user commands.

    Commands:
        r  — regenerate a new maze (new random seed)
        p  — toggle shortest-path display
        c  — cycle wall colour scheme
        q  — quit

    Args:
        gen: Already-generated MazeGenerator instance.
        config: Parsed config (used to rebuild generator on regenerate).
        output_file: Path to write hex output.
    """
    show_path = False
    color_idx: int = 0

    while True:
        _clear()
        scheme = COLOR_SCHEMES[color_idx]
        print(render_maze(gen, show_path=show_path, scheme=scheme))
        print()
        if not gen.has_pattern:
            print("[!] Maze too small to embed '42' pattern.")
        if show_path:
            if gen.solution:
                print(f"[Path shown] Length: {len(gen.solution)} steps")
            else:
                print("[!] No solution found.")
        print(f"[Colour: {scheme.name}]")
        print()
        print(
            "Commands:  [r] regenerate   [p] toggle path"
            "   [c] cycle colour   [q] quit"
        )
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break
        elif cmd == "r":
            new_seed = random.randint(0, 2**31)
            gen = MazeGenerator(
                width=gen.width,
                height=gen.height,
                entry=gen.entry,
                exit_cell=gen.exit_cell,
                seed=new_seed,
                perfect=gen.perfect,
            )
            gen.generate()
            try:
                write_output(gen, output_file)
            except OSError as e:
                print(f"[!] Could not write output file: {e}")
                input("Press Enter to continue...")
        elif cmd == "p":
            show_path = not show_path
        elif cmd == "c":
            color_idx = (color_idx + 1) % len(COLOR_SCHEMES)


# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Parse config, generate maze, write output, start display loop."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]

    try:
        config = parse_config(config_path)
        gen, output_file = build_generator(config)
        gen.generate()
    except (FileNotFoundError, ValueError) as e:
        print(f"[Error] {e}", file=sys.stderr)
        sys.exit(1)

    if not gen.has_pattern:
        print(
            "[Warning] Maze is too small to embed the '42' pattern "
            f"(need at least {MIN_WIDTH}x{MIN_HEIGHT} cells).",
            file=sys.stderr,
        )

    try:
        write_output(gen, output_file)
    except OSError as e:
        print(f"[Error] Could not write output file: {e}", file=sys.stderr)
        sys.exit(1)

    display_loop(gen, config, output_file)


if __name__ == "__main__":
    main()
