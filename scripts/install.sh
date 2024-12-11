#!/bin/bash

# Install necessary dependencies.

if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install python@3.12
    brew install --cask claude
elif [[ "$OSTYPE" == "msys" ]]; then
    choco install python --version=3.12
    echo "Please manually install Claude for Windows."
else
    echo "Unsupported OS."
fi
