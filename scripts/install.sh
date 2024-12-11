#!/bin/bash

# Install necessary dependencies.

brew install python@3.12

if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install --cask claude
fi
