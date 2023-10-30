#! /usr/bin/env bash


POETRY_ROOT_DIR="$HOME/.poetry-root"
mkdir "$POETRY_ROOT_DIR"

poetry config cache-dir "${POETRY_ROOT_DIR}/.cache"
poetry config virtualenvs.in-project false

poetry install

echo 'Done installing dependencies!'
