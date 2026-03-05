# скрипты для just

alias isort := sort-imports
alias rund := run-docker
alias downd := down-docker
alias reld := reload-docker
alias logd := logs-docker

default_compose_file := 'docker-compose.yml'
default_service := 'app'
venv := 'source ./.venv/bin/activate &&'
mig := 'main>demo'

sort-imports:
    uv run ruff check --select I --fix .

lint:
    uv run deptry .
    just isort
    uv run ruff check --fix

run:
    uv run main.py

run-docker file=default_compose_file:
    just lint
    just test
    docker-compose -f {{file}} up --build -d

down-docker:
    docker-compose down

reload-docker file=default_compose_file:
    docker-compose down
    just rund {{file}}

logs-docker:
    docker-compose logs --follow

test:
    uv run pytest --cov=.

coverage:
    uv run pytest --cov --cov-report=html
    xdg-open "htmlcov/index.html"

push:
    just lint
    just test
    git push

rundl file=default_compose_file:
    just rund {{file}}
    just logd

connect service=default_service:
    docker-compose exec {{service}} bash

checkout migration=mig:
    uv run checkout_helper.py -m '{{migration}}' -y