#!/usr/bin/env python3
"""
Kubernetes deployment script for Agentic Neurodata Conversion.

This script handles deployment to Kubernetes clusters with proper
configuration management and health checks.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Optional


class KubernetesDeployer:
    """Manages Kubernetes deployment operations."""

    def __init__(self, project_root: Path, namespace: str = "agentic-neurodata"):
        self.project_root = project_root
        self.namespace = namespace
        self.k8s_dir = project_root / "k8s"

    def run_command(
        self, command: list[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a kubectl command with proper error handling."""
        print(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                check=check,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            if check:
                sys.exit(1)
            return e

    def check_prerequisites(self) -> bool:
        """Check if kubectl is available and cluster is accessible."""
        try:
            self.run_command(["kubectl", "version", "--client"])
            self.run_command(["kubectl", "cluster-info"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: kubectl is required and cluster must be accessible.")
            print("Please install kubectl and configure cluster access.")
            return False

    def create_namespace(self) -> None:
        """Create the namespace if it doesn't exist."""
        print(f"Creating namespace: {self.namespace}")
        self.run_command(
            ["kubectl", "apply", "-f", str(self.k8s_dir / "namespace.yaml")]
        )

    def apply_configmaps(self) -> None:
        """Apply ConfigMaps."""
        print("Applying ConfigMaps...")
        self.run_command(
            ["kubectl", "apply", "-f", str(self.k8s_dir / "configmap.yaml")]
        )

    def apply_storage(self) -> None:
        """Apply storage resources (PVCs)."""
        print("Applying storage resources...")
        self.run_command(["kubectl", "apply", "-f", str(self.k8s_dir / "pvc.yaml")])

    def build_and_push_image(
        self, image_tag: str, registry: Optional[str] = None
    ) -> str:
        """Build and push Docker image."""
        if registry:
            full_image_name = f"{registry}/agentic-neurodata-conversion:{image_tag}"
        else:
            full_image_name = f"agentic-neurodata-conversion:{image_tag}"

        print(f"Building Docker image: {full_image_name}")

        # Build image
        self.run_command(
            [
                "docker",
                "build",
                "-t",
                full_image_name,
                "-f",
                "Dockerfile",
                "--target",
                "production",
                ".",
            ]
        )

        # Push image if registry is specified
        if registry:
            print(f"Pushing image to registry: {full_image_name}")
            self.run_command(["docker", "push", full_image_name])

        return full_image_name

    def update_deployment_image(self, image_name: str) -> None:
        """Update deployment with new image."""
        print(f"Updating deployment with image: {image_name}")
        self.run_command(
            [
                "kubectl",
                "set",
                "image",
                "deployment/agentic-mcp-server",
                f"mcp-server={image_name}",
                "-n",
                self.namespace,
            ]
        )

    def apply_deployment(self) -> None:
        """Apply deployment resources."""
        print("Applying deployment...")
        self.run_command(
            ["kubectl", "apply", "-f", str(self.k8s_dir / "deployment.yaml")]
        )

    def apply_ingress(self) -> None:
        """Apply ingress resources."""
        print("Applying ingress...")
        self.run_command(["kubectl", "apply", "-f", str(self.k8s_dir / "ingress.yaml")])

    def wait_for_deployment(self, timeout: int = 300) -> bool:
        """Wait for deployment to be ready."""
        print("Waiting for deployment to be ready...")
        try:
            self.run_command(
                [
                    "kubectl",
                    "rollout",
                    "status",
                    "deployment/agentic-mcp-server",
                    "-n",
                    self.namespace,
                    f"--timeout={timeout}s",
                ]
            )
            return True
        except subprocess.CalledProcessError:
            print("Deployment failed to become ready within timeout")
            return False

    def get_service_info(self) -> dict[str, Any]:
        """Get service information."""
        try:
            result = self.run_command(
                [
                    "kubectl",
                    "get",
                    "service",
                    "agentic-mcp-service",
                    "-n",
                    self.namespace,
                    "-o",
                    "json",
                ]
            )

            import json

            service_info = json.loads(result.stdout)
            return service_info
        except Exception as e:
            print(f"Failed to get service info: {e}")
            return {}

    def get_ingress_info(self) -> dict[str, Any]:
        """Get ingress information."""
        try:
            result = self.run_command(
                [
                    "kubectl",
                    "get",
                    "ingress",
                    "agentic-ingress",
                    "-n",
                    self.namespace,
                    "-o",
                    "json",
                ],
                check=False,
            )

            if result.returncode == 0:
                import json

                ingress_info = json.loads(result.stdout)
                return ingress_info
            else:
                return {}
        except Exception as e:
            print(f"Failed to get ingress info: {e}")
            return {}

    def show_status(self) -> None:
        """Show deployment status."""
        print("\n" + "=" * 50)
        print("DEPLOYMENT STATUS")
        print("=" * 50)

        # Pods
        print("\nPods:")
        self.run_command(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.namespace,
                "-l",
                "app.kubernetes.io/name=agentic-neurodata-conversion",
            ]
        )

        # Services
        print("\nServices:")
        self.run_command(["kubectl", "get", "services", "-n", self.namespace])

        # Ingress
        print("\nIngress:")
        self.run_command(
            ["kubectl", "get", "ingress", "-n", self.namespace], check=False
        )

        # Get access information
        service_info = self.get_service_info()
        ingress_info = self.get_ingress_info()

        print("\n" + "=" * 50)
        print("ACCESS INFORMATION")
        print("=" * 50)

        if ingress_info and "spec" in ingress_info:
            rules = ingress_info.get("spec", {}).get("rules", [])
            if rules:
                for rule in rules:
                    host = rule.get("host", "")
                    if host:
                        print(f"External URL: https://{host}")

        if service_info:
            cluster_ip = service_info.get("spec", {}).get("clusterIP", "")
            port = service_info.get("spec", {}).get("ports", [{}])[0].get("port", "")
            if cluster_ip and port:
                print(f"Cluster IP: {cluster_ip}:{port}")

        print("\nTo access via port-forward:")
        print(
            f"kubectl port-forward service/agentic-mcp-service 8000:8000 -n {self.namespace}"
        )

    def show_logs(self, follow: bool = False) -> None:
        """Show application logs."""
        command = [
            "kubectl",
            "logs",
            "-l",
            "app.kubernetes.io/component=mcp-server",
            "-n",
            self.namespace,
        ]

        if follow:
            command.append("-f")

        self.run_command(command)

    def delete_deployment(self) -> None:
        """Delete all deployment resources."""
        print("Deleting deployment resources...")

        resources = ["ingress.yaml", "deployment.yaml", "pvc.yaml", "configmap.yaml"]

        for resource in resources:
            resource_path = self.k8s_dir / resource
            if resource_path.exists():
                self.run_command(
                    ["kubectl", "delete", "-f", str(resource_path)], check=False
                )

    def deploy_full(
        self, image_tag: str = "latest", registry: Optional[str] = None
    ) -> None:
        """Deploy the complete application."""
        print("Starting full deployment...")

        # Get image tag and registry from environment if not provided
        if image_tag == "latest":
            image_tag = os.getenv("IMAGE_TAG", "latest")
        if not registry:
            registry = os.getenv("REGISTRY")

        # Build and push image
        image_name = self.build_and_push_image(image_tag, registry)

        # Apply resources in order
        self.create_namespace()
        self.apply_configmaps()
        self.apply_storage()
        self.apply_deployment()

        # Update image if different from default
        if image_name != "agentic-neurodata-conversion:latest":
            self.update_deployment_image(image_name)

        # Wait for deployment
        if self.wait_for_deployment():
            print("Deployment successful!")

            # Apply ingress (optional)
            try:
                self.apply_ingress()
            except subprocess.CalledProcessError:
                print("Warning: Ingress deployment failed (may not be configured)")

            self.show_status()
        else:
            print("Deployment failed!")
            sys.exit(1)


def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy Agentic Neurodata Conversion to Kubernetes"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy application")
    deploy_parser.add_argument("--image-tag", default="latest", help="Docker image tag")
    deploy_parser.add_argument("--registry", help="Docker registry URL")
    deploy_parser.add_argument(
        "--namespace", default="agentic-neurodata", help="Kubernetes namespace"
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update deployment")
    update_parser.add_argument("--image-tag", default="latest", help="Docker image tag")
    update_parser.add_argument("--registry", help="Docker registry URL")
    update_parser.add_argument(
        "--namespace", default="agentic-neurodata", help="Kubernetes namespace"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show deployment status")
    status_parser.add_argument(
        "--namespace", default="agentic-neurodata", help="Kubernetes namespace"
    )

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show application logs")
    logs_parser.add_argument(
        "--namespace", default="agentic-neurodata", help="Kubernetes namespace"
    )
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete deployment")
    delete_parser.add_argument(
        "--namespace", default="agentic-neurodata", help="Kubernetes namespace"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize deployer
    project_root = Path(__file__).parent.parent
    deployer = KubernetesDeployer(project_root, args.namespace)

    # Check prerequisites
    if not deployer.check_prerequisites():
        return

    # Execute command
    try:
        if args.command == "deploy":
            deployer.deploy_full(args.image_tag, args.registry)

        elif args.command == "update":
            image_name = deployer.build_and_push_image(args.image_tag, args.registry)
            deployer.update_deployment_image(image_name)
            if deployer.wait_for_deployment():
                print("Update successful!")
                deployer.show_status()
            else:
                print("Update failed!")
                sys.exit(1)

        elif args.command == "status":
            deployer.show_status()

        elif args.command == "logs":
            deployer.show_logs(args.follow)

        elif args.command == "delete":
            deployer.delete_deployment()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
