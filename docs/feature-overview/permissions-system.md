# Feature-Based Permissions System

## Overview
Sonic Brief implements a granular, feature-based permissions system for both frontend and backend, enabling fine-grained access control per user.

### Key Concepts
- **Feature Toggles**: Each feature (e.g., `CREATE_JOBS`, `MANAGE_USERS`) is a boolean toggle per user.
- **Role Templates**: Predefined sets of features for quick user setup (User, Editor, Admin).
- **API Integration**: Permissions are synchronized between frontend and backend via RESTful endpoints.
- **Migration Plan**: Stepwise migration from legacy string/role-based permissions to the new system, with backward compatibility.

### Implementation
- **Frontend**: Uses enums and hooks for permission checks, UI guards, and feature management dialogs.
- **Backend**: Enforces permissions at route and business logic levels using FastAPI dependencies.
- **Testing**: Comprehensive unit, integration, and E2E tests for permission logic.

### Documentation
- See `frontend_app/docs/simplified-permissions-system.md` and `frontend_app/PERMISSION_MIGRATION_GUIDE.md` for migration steps, usage examples, and API details.
