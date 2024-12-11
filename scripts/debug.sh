#!/bin/bash

npx @modelcontextprotocol/inspector \
    uv \
    --directory "$1" \
    run \
    server
