#!/bin/bash

# Creates virtual environments and install basic dependencies.

export UV_PROJECT_ENVIRONMENT="env"

directories=("nhl" "yahoo")

for dir in "${directories[@]}"; do
    cd "$dir" || exit
    uv venv env --python 3.12
    
    if [[ "$OSTYPE" == "msys" ]]; then
        # shellcheck disable=SC1091
        source env/Scripts/activate
    else
        # shellcheck disable=SC1091
        source env/bin/activate
    fi
    
    uv pip install httpx mcp
    deactivate
    cd ..
done
