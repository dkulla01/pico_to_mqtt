#! /usr/bin/env bash


poetry_root_dir="$HOME/.poetry-root"
poetry_cache_dir="${poetry_root_dir}/.cache"
poetry_virtualenv_dir="${poetry_cache_dir}/virtualenvs"

mkdir "$poetry_root_dir"

# create a virtualenv for poetry to install things into
virtualenv_name="pico-to-mqtt"
python -m venv "${poetry_virtualenv_dir}/${virtualenv_name}"

poetry config cache-dir "$poetry_cache_dir"

#don't create a new virtualenv. use the virtualenv we already created
poetry config virtualenvs.create false

source "${poetry_virtualenv_dir}/${virtualenv_name}/bin/activate"
poetry install

echo 'Done installing dependencies!'
