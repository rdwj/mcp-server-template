.PHONY: install run dev test test-preview docker k8s-apply k8s-delete podman podman-up oc-setup oc-bc-start oc-bc-logs oc-bc-binary oc-bc-binary-start

VENV ?=.venv
PY ?=python

HAS_UV := $(shell command -v uv 2>/dev/null)

install:
ifdef HAS_UV
	uv sync
else
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate; pip install -U pip; pip install -e .
endif

run:
	MCP_HOT_RELOAD=1 MCP_TRANSPORT=stdio $(PY) -m src.main

dev: install run

test:
ifdef HAS_UV
	uv run pytest -q
else
	. $(VENV)/bin/activate; pytest -q
endif

# Focused test for the prompt preview CLI
# Usage: make test-preview  (runs tests/test_preview_prompt.py only)
# You can pass -k filters: make test-preview ARGS="-k missing_schema"
TEST_PREVIEW_PATH := tests/test_preview_prompt.py

test-preview:
ifdef HAS_UV
	uv run pytest -q $(TEST_PREVIEW_PATH) $(ARGS)
else
	. $(VENV)/bin/activate; pytest -q $(TEST_PREVIEW_PATH) $(ARGS)
endif

docker:
	docker build -t fastmcp-unified:latest .

podman:
	podman build -t localhost/fastmcp-unified:latest -f Containerfile .

podman-up:
	podman-compose up --build -d

k8s-apply:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/imagestream.yaml
	kubectl apply -f k8s/buildconfig.yaml || true
	kubectl apply -f k8s/buildconfig-binary.yaml || true
	kubectl apply -f k8s/configmap-prompts.yaml || true
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/route.yaml || true
	kubectl apply -f k8s/hpa.yaml

k8s-delete:
	kubectl delete -f k8s/hpa.yaml --ignore-not-found
	kubectl delete -f k8s/route.yaml --ignore-not-found
	kubectl delete -f k8s/service.yaml --ignore-not-found
	kubectl delete -f k8s/deployment.yaml --ignore-not-found
	kubectl delete -f k8s/configmap-prompts.yaml --ignore-not-found
	kubectl delete -f k8s/buildconfig.yaml --ignore-not-found
	kubectl delete -f k8s/buildconfig-binary.yaml --ignore-not-found
	kubectl delete -f k8s/imagestream.yaml --ignore-not-found
	kubectl delete -f k8s/namespace.yaml --ignore-not-found

oc-setup:
	oc project mcp || oc new-project mcp
	oc apply -f k8s/imagestream.yaml
	oc apply -f k8s/buildconfig.yaml

oc-bc-start:
	oc start-build fastmcp-unified --follow --wait -n mcp || true

oc-bc-logs:
	oc logs bc/fastmcp-unified -n mcp --follow

# Start a binary build using the current directory
oc-bc-binary:
	oc project mcp || oc new-project mcp
	oc apply -f k8s/imagestream.yaml
	oc apply -f k8s/buildconfig-binary.yaml

oc-bc-binary-start:
	oc start-build fastmcp-unified-binary --from-dir=. --follow --wait -n mcp
