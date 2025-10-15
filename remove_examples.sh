#!/bin/bash
#
# Remove all example content from the MCP server project
#
# This script removes:
# - Example tools, resources, prompts, and middleware
# - Example tests
# - Example documentation
#
# This is recommended to prevent examples from cluttering your AI assistant's
# context window when working on your actual implementation.
#

set -e

echo "🧹 Removing example content..."

# Remove example directories
if [ -d "src/tools/examples" ]; then
    rm -rf src/tools/examples
    echo "✓ Removed src/tools/examples"
fi

if [ -d "src/resources/examples" ]; then
    rm -rf src/resources/examples
    echo "✓ Removed src/resources/examples"
fi

if [ -d "src/prompts/examples" ]; then
    rm -rf src/prompts/examples
    echo "✓ Removed src/prompts/examples"
fi

if [ -d "src/middleware/examples" ]; then
    rm -rf src/middleware/examples
    echo "✓ Removed src/middleware/examples"
fi

# Remove example tests
if [ -d "tests/examples" ]; then
    rm -rf tests/examples
    echo "✓ Removed tests/examples"
fi

# Remove the preview_prompt utility (it was for testing examples)
if [ -f "src/tools/_preview_prompt_utility.py" ]; then
    rm -f src/tools/_preview_prompt_utility.py
    echo "✓ Removed preview_prompt utility"
fi

echo ""
echo "✅ All examples removed!"
echo ""
echo "Your MCP server now has a clean slate."
echo "Use 'fips-agents generate' to create new components."
