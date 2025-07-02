# Sonic Brief: Major Features Overview

This document provides a high-level summary of the major features and architectural components of the Sonic Brief project, based on a crawl of the codebase and documentation.

---

## 1. End-to-End Audio Transcription & Summarization Workflow
- **User uploads voice recording** via the Azure Static Web App (React frontend).
- **Azure App Service** stores the file in Azure Blob Storage and triggers an **Azure Function**.
- **Azure Function**:
  - Submits the file to Azure Speech-to-Text for transcription.
  - Stores the transcription in Blob Storage and updates CosmosDB.
  - Retrieves a prompt from CosmosDB and sends the transcription to Azure OpenAI GPT-4o for summarization.
  - Stores the summary in Blob Storage and updates CosmosDB with completion status.
- **Frontend** fetches and displays transcripts, summaries, and allows report download.

## 2. Modular Backend API (FastAPI)
- RESTful API with clear resource naming and HTTP methods.
- JWT-based authentication and granular permission system.
- Modular routers: authentication, upload, prompts, analytics, logout, etc.
- CosmosDB for user, job, and prompt data.
- Blob Storage for file management.

## 3. Granular Feature-Based Permissions System
- **Frontend**: Uses feature toggles (e.g., `CREATE_JOBS`, `MANAGE_USERS`) for per-user access control.
- **Backend**: Enforces permissions at both route and business logic levels.
- **Migration guides** and stepwise plans for moving from legacy to new system.

## 4. User Management Enhancements
- Bulk user actions, advanced filters, permission delegation, and test utilities.
- Responsive, accessible UI with visual feedback and comprehensive testing strategy.

## 5. Analytics & System Health
- Refactored analytics system with event batching, real-time updates, and dashboard integration.
- System health metrics (API response time, etc.) surfaced in the frontend.
- Migration plan for analytics infrastructure and data models.

## 6. Infrastructure as Code (Terraform)
- Automated deployment of all Azure resources: App Service, Static Web App, CosmosDB, Blob Storage, OpenAI, Speech, Log Analytics, etc.
- Modular, documented Terraform scripts for reproducible environments.

## 7. Modern Frontend Stack
- **Vite + React + Typescript + Tailwind CSS** for rapid, type-safe UI development.
- **TanStack Router** for modular, file-based routing.
- **React Query** for data fetching and caching.
- UI/UX best practices: accessibility, responsive design, and state management.

## 8. Documentation & Migration Plans
- Detailed guides for permission system migration, analytics refactor, and user management enhancements.
- Stepwise execution plans for major revamps, ensuring backward compatibility and test coverage.

---

For more details, see the sub-feature documents in this folder.
