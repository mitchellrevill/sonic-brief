# Infrastructure as Code (IaC)

## Overview
All Azure resources for Sonic Brief are provisioned and managed using Terraform, ensuring reproducibility and easy environment management.

### Major Components
- **App Service (Backend API)**: Linux-based, managed identity, CORS, authentication.
- **Static Web App (Frontend)**: Automated deployment, integrated with backend.
- **CosmosDB**: Serverless, geo-redundant, multiple containers for auth, jobs, prompts.
- **Blob Storage**: Private containers for recordings, transcriptions, and results.
- **Azure OpenAI & Speech**: Custom deployments, managed identity, diagnostic logging.
- **Log Analytics**: Centralized logging, 30-day retention.

### Best Practices
- Modular Terraform scripts for each resource.
- Output variables for resource names and connection strings.
- Validation and troubleshooting steps included in documentation.

### Documentation
- See `infra/README.md` and Terraform files in `infra/` for details.
