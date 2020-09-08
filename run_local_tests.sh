#!/bin/bash

# make conda work in the shell script as it does in regular terminal
eval "$(conda shell.bash hook)"

PROJECT_ENV_NAME='switch_env'
STARTING_ENV=$CONDA_DEFAULT_ENV

# make sure we're in the correct env
if [[ ${CONDA_DEFAULT_ENV} != ${PROJECT_ENV_NAME} ]]; then
    conda activate $PROJECT_ENV_NAME
fi

coverage run -m unittest && coverage report -m

# go back to whatever env you were in before
if [[ ${CONDA_DEFAULT_ENV} != ${STARTING_ENV} ]]; then
    conda activate $STARTING_ENV
fi