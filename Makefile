PYTHON = python3
MAIN   = a_maze_ing.py
CONFIG = config.txt
VENV   = .venv

.PHONY: install run debug clean lint lint-strict build-pkg

install:
	$(PYTHON) -m pip install flake8 mypy build

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	rm -f maze.txt

lint:
	flake8 . --exclude build,dist
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	       --disallow-untyped-defs --check-untyped-defs --exclude build

lint-strict:
	flake8 . --exclude build,dist
	mypy . --strict --exclude build

build-pkg:
	$(PYTHON) -m build --wheel --sdist
