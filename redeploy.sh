#!/bin/bash
# Quick redeploy script after code changes
# Usage: ./redeploy.sh [project-name]

set -e

PROJECT=${1:-mcp-demo}

echo "========================================="
echo "Redeploying MCP Server to OpenShift"
echo "========================================="
echo "Project: $PROJECT"
echo ""

# Start build
echo "→ Rebuilding container image..."
oc start-build mcp-server --from-dir=. --follow -n $PROJECT

# Restart deployment to pull new image
echo "→ Restarting deployment..."
oc rollout restart deployment/mcp-server -n $PROJECT
oc rollout status deployment/mcp-server -n $PROJECT --timeout=300s

# Get route
ROUTE=$(oc get route mcp-server -n $PROJECT -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

echo ""
echo "========================================="
echo "✅ Redeployment Complete!"
echo "========================================="
if [ -n "$ROUTE" ]; then
    echo "MCP Server URL: https://$ROUTE/mcp/"
    echo ""
    echo "Test with MCP Inspector:"
    echo "  npx @modelcontextprotocol/inspector https://$ROUTE/mcp/"
fi
echo "========================================="