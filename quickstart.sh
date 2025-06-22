#!/bin/bash

# Auth0 Export - Quickstart Script
# This script allows users to run the tool directly from GitHub

set -e

echo "🚀 Auth0 Export Tool - Quickstart"
echo "================================="
echo ""

# Check if uvx is available
if ! command -v uvx &> /dev/null; then
    echo "❌ uvx not found. Please install uv first:"
    echo ""
    echo "  # On macOS/Linux:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "  # On Windows:"
    echo "  powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    echo ""
    echo "  # Or install via pip:"
    echo "  pip install uv"
    echo ""
    exit 1
fi

echo "✅ Found uvx - running Auth0 Export..."
echo ""

# Run the tool with uvx
exec uvx --from git+https://github.com/baocin/auth0-export auth0-export "$@"