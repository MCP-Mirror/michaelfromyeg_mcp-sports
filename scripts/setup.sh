#!/bin/bash

# Creates virtual environments and install basic dependencies.

directories=("nhl" "yahoo")

for dir in "${directories[@]}"; do
    cd "$dir" || exit
    uv venv env --python 3.12
    # shellcheck disable=SC1091
    source env/bin/activate
    uv pip install httpx mcp
    deactivate
    cd ..
done
