BIN := node_modules/.bin
VENV := .venv/bin
export PLAYWRIGHT_BROWSERS_PATH := 0

CHECKS := lint-js lint-py types-js types-py unit-js unit-py ui

.PHONY: test serve setup sounds $(CHECKS)

test: ## run all checks in parallel and print a summary
	@tools/check.sh $(CHECKS)

serve: ## serve the soundboard at http://localhost:8000
	python3 -m http.server 8000

setup: ## once: npm packages, .venv with ruff + mypy, Chromium for UI tests
	npm install
	python3 -m venv .venv
	$(VENV)/pip install -r requirements-dev.txt
	$(BIN)/playwright install chromium

sounds: ## regenerate the built-in sounds (macOS say + ffmpeg)
	python3 tools/make_sounds.py

lint-js: ; $(BIN)/biome lint *.js tests
lint-py: ; $(VENV)/ruff check tools tests
types-js: ; $(BIN)/tsc
types-py: ; $(VENV)/mypy --strict tools tests
unit-js: ; node --test tests/*.test.js
unit-py: ; $(VENV)/python -m unittest discover -s tests
ui: ; $(BIN)/playwright test --reporter=line
