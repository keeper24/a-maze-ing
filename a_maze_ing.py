"""A-Maze-ing: maze generator entry point.

Usage::

    python3 a_maze_ing.py config.txt
"""

import sys
import os
from typing import Optional
from mazegen import MazeGenerator, NORTH, EAST, SOUTH, WEST

# ──────────────────────────────────────────────────────────────────────────────
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
                        f"Config line {lineno}: expected KEY=VALUE, got: {line!r}"
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
    """Validate config values and return a configured MazeGenerator + output path.

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
            raise ValueError(f"{key} coordinates must be integers, got: {raw!r}")

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


# ──────────────────────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────────────────────
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


def render_maze(
    gen: MazeGenerator,
    show_path: bool = False,
    show_42: bool = True,
) -> str:
    """Render the maze as a multi-line ASCII string.

    Args:
        gen: A MazeGenerator that has already run generate().
        show_path: If True, overlay the solution path with '*'.
        show_42: If True, shade the '42' cells with '#'.

    Returns:
        String ready to print to the terminal.
    """
    grid = gen.grid
    height = gen.height
    width = gen.width
    ec, er = gen.entry
    xc, xr = gen.exit_cell

    # Build path cells set
    path_cells: set[tuple[int, int]] = set()
    if show_path and gen.solution:
        col, row = gen.entry
        path_cells.add((col, row))
        dir_map = {"N": NORTH, "E": EAST, "S": SOUTH, "W": WEST}
        from mazegen import DELTA
        for letter in gen.solution:
            dc, dr = DELTA[dir_map[letter]]
            col += dc
            row += dr
            path_cells.add((col, row))

    lines: list[str] = []

    # Each cell takes 2 chars wide + 1 for junctions → (width*2 + 1) chars per row
    # Each cell takes 1 char tall + 1 for junctions → (height*2 + 1) rows

    for r in range(height + 1):
        line_top = ""   # junction + horizontal wall row
        line_mid = ""   # vertical wall + cell interior row (only for r < height)

        for c in range(width + 1):
            # Junction character at corner (r, c)
            line_top += _junction(grid, r, c)

            if c < width:
                # Horizontal segment: top wall of cell (r, c) if r < height,
                # else bottom wall of cell (r-1, c)
                if r < height:
                    has_top = bool(grid[r][c] & NORTH)
                else:
                    has_top = bool(grid[r - 1][c] & SOUTH)
                line_top += _HORIZ + _HORIZ if has_top else "  "

        lines.append(line_top)

        if r < height:
            for c in range(width + 1):
                # Vertical segment: left wall of cell (r, c)
                if c < width:
                    has_left = bool(grid[r][c] & WEST)
                else:
                    has_left = bool(grid[r][c - 1] & EAST)
                line_mid += _VERT if has_left else " "

                if c < width:
                    # Cell interior
                    if (c, r) == (ec, er):
                        interior = "S "
                    elif (c, r) == (xc, xr):
                        interior = "E "
                    elif show_42 and (c, r) in gen.forty_two_cells:
                        interior = "##"
                    elif show_path and (c, r) in path_cells:
                        interior = "* "
                    else:
                        interior = "  "
                    line_mid += interior

            lines.append(line_mid)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Interactive display loop
# ──────────────────────────────────────────────────────────────────────────────

def _clear() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def display_loop(gen: MazeGenerator, config: dict[str, str], output_file: str) -> None:
    """Interactive loop: display maze and respond to user commands.

    Commands:
        r  — regenerate a new maze (new random seed)
        p  — toggle shortest-path display
        q  — quit

    Args:
        gen: Already-generated MazeGenerator instance.
        config: Parsed config dictionary (for reconstructing gen on regenerate).
        output_file: Path to write hex output.
    """
    show_path = False
    import random as _rnd

    while True:
        _clear()
        print(render_maze(gen, show_path=show_path))
        print()
        if not gen.has_pattern:
            print("[!] Maze too small to embed '42' pattern.")
        if show_path:
            if gen.solution:
                print(f"[Path shown] Length: {len(gen.solution)} steps")
            else:
                print("[!] No solution found.")
        print()
        print("Commands:  [r] regenerate   [p] toggle path   [q] quit")
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break
        elif cmd == "r":
            new_seed = _rnd.randint(0, 2**31)
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
        else:
            pass  # Ignore unknown commands silently


# ──────────────────────────────────────────────────────────────────────────────
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
    except (FileNotFoundError, ValueError) as e:
        print(f"[Error] {e}", file=sys.stderr)
        sys.exit(1)

    gen.generate()

    if not gen.has_pattern:
        print(
            "[Warning] Maze is too small to embed the '42' pattern "
            f"(need at least {11}x{9} cells).",
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
