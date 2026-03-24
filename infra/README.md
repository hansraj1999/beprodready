# Infrastructure (Archai)

This folder is reserved for deployment and platform configuration beyond local Docker Compose.

Typical additions as the product grows:

- **Container orchestration** — Kubernetes manifests or Helm charts (`deployments/`, `services/`, `ingress`).
- **IaC** — Terraform or OpenTofu modules for VPC, databases, and managed services.
- **CI/CD** — Pipeline definitions if you keep them in-repo (e.g. GitHub Actions called from here via reusable workflows).

The root `docker-compose.yml` is the canonical reference for running the full stack locally. For production, prefer immutable images, secrets managers, and managed databases rather than Compose on a single VM unless that matches your operational model.
