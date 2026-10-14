.PHONY: setup lint test data baselines sim all docker-build docker-test

setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest -q

# Fases 1, 2 e 3/4: os módulos abaixo serão criados pelo agente seguindo docs/specs/.
data:
	uv run python -m tcc.data.build

baselines:
	uv run python -m tcc.forecast.run

sim:
	uv run python -m tcc.sim.run

all: data baselines sim

docker-build:
	docker compose build

docker-test:
	docker compose run --rm app make test
