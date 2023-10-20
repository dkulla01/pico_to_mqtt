#! /usr/bin/env bash

WORKSPACE_DIR="$(pwd)"

poetry config cache-dir "${WORKSPACE_DIR}/.cache"
poetry config virtualenvs.in-project true

poetry install

echo 'done installing dependencies!'
