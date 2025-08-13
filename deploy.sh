#!/bin/bash
# Simple deployment script for MCP server to OpenShift
# Usage: ./deploy.sh [project-name]

set -e

PROJECT=${1:-mcp-demo}

echo "========================================="
echo "MCP Server Deployment to OpenShift"
echo "========================================="
echo "Project: $PROJECT"
echo ""

# Check if logged in to OpenShift
if ! oc whoami &>/dev/null; then
    echo "Error: Not logged in to OpenShift. Please run 'oc login' first."
    exit 1
fi

# Create project if it doesn't exist
echo "→ Setting up project..."
if oc project $PROJECT &>/dev/null; then
    echo "  Using existing project: $PROJECT"
else
    echo "  Creating new project: $PROJECT"
    oc new-project $PROJECT
fi

# Apply OpenShift resources
echo "→ Applying OpenShift resources..."
sed "s|image: mcp-server:latest|image: image-registry.openshift-image-registry.svc:5000/$PROJECT/mcp-server:latest|g" openshift.yaml | oc apply -f - -n $PROJECT

# Start build
echo "→ Building container image..."
echo "  Starting binary build from current directory..."
oc start-build mcp-server --from-dir=. --follow -n $PROJECT

# Wait for rollout
echo "→ Deploying application..."
oc rollout restart deployment/mcp-server -n $PROJECT 2>/dev/null || true
oc rollout status deployment/mcp-server -n $PROJECT --timeout=300s

# Get route
ROUTE=$(oc get route mcp-server -n $PROJECT -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
if [ -n "$ROUTE" ]; then
    echo "MCP Server URL: https://$ROUTE/mcp/"
    echo ""
    echo "Test with MCP Inspector:"
    echo "  npx @modelcontextprotocol/inspector https://$ROUTE/mcp/"
else
    echo "Warning: Could not retrieve route URL"
fi
echo "========================================="