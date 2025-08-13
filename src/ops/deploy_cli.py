import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, check=check)


def prompt(default: str | None, label: str) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or (default or "")


def main() -> None:
    # Gather inputs
    project = prompt(os.getenv("MCP_OC_PROJECT", "mcp"), "OpenShift project (namespace)")
    app = prompt(os.getenv("MCP_APP_NAME", "fastmcp-unified"), "App name (deployment name)")
    transport = prompt(os.getenv("MCP_TRANSPORT", "http"), "Transport (http|stdio)")
    http_host = prompt(os.getenv("MCP_HTTP_HOST", "0.0.0.0"), "HTTP host")
    http_port = prompt(os.getenv("MCP_HTTP_PORT", "8080"), "HTTP port")
    http_path = prompt(os.getenv("MCP_HTTP_PATH", "/mcp/"), "HTTP path")
    allowed = prompt(os.getenv("MCP_HTTP_ALLOWED_ORIGINS", ""), "HTTP allowed origins (CSV, optional)")

    # Confirm
    print("\nDeploy settings:")
    print(json.dumps({
        "project": project,
        "app": app,
        "transport": transport,
        "http_host": http_host,
        "http_port": http_port,
        "http_path": http_path,
        "allowed_origins": allowed,
    }, indent=2))
    cont = prompt("y", "Proceed? (y/n)").lower()
    if cont not in {"y", "yes"}:
        print("Aborted.")
        sys.exit(1)

    # Switch project
    run(["oc", "project", project])

    # Apply IS/BC/Manifests
    k8s_dir = Path(__file__).resolve().parents[2] / "k8s"
    run(["oc", "apply", "-f", str(k8s_dir / "imagestream.yaml")])
    # Prefer binary BC if present; otherwise standard BC
    bc_binary = k8s_dir / "buildconfig-binary.yaml"
    bc_std = k8s_dir / "buildconfig.yaml"
    if bc_binary.exists():
        run(["oc", "apply", "-f", str(bc_binary)])
    if bc_std.exists():
        run(["oc", "apply", "-f", str(bc_std)])

    # Start binary build if possible; fall back to normal BC
    if bc_binary.exists():
        run(["oc", "start-build", "fastmcp-unified-binary", "--from-dir=.", "--follow", "--wait", "-n", project])
    else:
        print("No binary BuildConfig. If using Git BC, ensure repo URL is configured, then start the build manually.")

    # Patch deployment env from inputs (idempotent oc set env)
    run(["oc", "apply", "-f", str(k8s_dir / "namespace.yaml")])
    run(["oc", "apply", "-f", str(k8s_dir / "configmap-prompts.yaml")])
    run(["oc", "apply", "-f", str(k8s_dir / "service.yaml")])
    run(["oc", "apply", "-f", str(k8s_dir / "route.yaml")])
    run(["oc", "apply", "-f", str(k8s_dir / "hpa.yaml")])
    run(["oc", "apply", "-f", str(k8s_dir / "deployment.yaml")])

    run([
        "oc", "set", "env", f"deployment/{app}",
        f"MCP_TRANSPORT={transport}",
        f"MCP_HTTP_HOST={http_host}",
        f"MCP_HTTP_PORT={http_port}",
        f"MCP_HTTP_PATH={http_path}",
        f"MCP_HTTP_ALLOWED_ORIGINS={allowed}",
        "-n", project
    ])

    # Wait for rollout and print route
    run(["oc", "rollout", "status", f"deploy/{app}", "-n", project])
    subprocess.run(["bash", "-lc", f"oc get route {app} -n {project} -o jsonpath='{{.spec.host}}\n'"])


if __name__ == "__main__":
    main()
