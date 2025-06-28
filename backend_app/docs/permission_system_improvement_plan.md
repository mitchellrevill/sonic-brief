# Permission System Improvement Plan for AI Implementation

## Objective
Enhance the Sonic Brief permission system for maintainability, security, and scalability, following best practices and the revamp instructions.

---

## Stepwise Plan

### 1. Type Safety & Consistency
- Refactor all backend permission checks to use the `PermissionLevel` enum, not raw strings.
- Ensure all frontend permission logic uses TypeScript enums/types that match the backend.
- (Optional) Generate frontend permission types from backend source.

### 2. Centralized Capability Check Utility
- Backend: Implement a `can(user, action: str) -> bool` utility for checking capabilities.
- Frontend: Implement a `useCan(action: string): boolean` hook or utility for React.
- Refactor all code to use these utilities for permission checks.

### 3. Dynamic/Custom Capabilities
- Add support for a `custom_capabilities` field in user/org profiles.
- Merge custom capabilities with defaults in backend logic.
- Expose merged capabilities to the frontend.

### 4. Audit Logging
- Log all permission changes and access denials for sensitive actions.
- Store audit logs in a dedicated collection/table.

### 5. Granular Resource Permissions
- Ensure all resource-level permissions (e.g., job sharing) are enforced using a `shared_with` or ACL structure.
- Add/expand utility functions for resource-level permission checks.

### 6. Permission Delegation
- Allow admins to delegate specific permissions to other users for specific resources.
- Add endpoints and UI for delegation.

### 7. Testing & Validation
- Add/expand automated tests for all permission checks and edge cases.
- Add a test utility to simulate users with different permissions/capabilities.

### 8. Documentation Automation
- Generate frontend permission constants/types from backend source or a shared schema.
- Auto-generate permission documentation from code.

### 9. Performance
- Evaluate and, if needed, implement a distributed cache (e.g., Redis) for permission lookups.

### 10. Error Handling & Messaging
- Improve error messages for permission denials, including which capability is missing.

---

## Implementation Guidelines
- Follow the revamp stepwise execution: foundational models first, then new modules/utilities, then refactor usages, then remove legacy code, then add tests/docs.
- Communicate each step and its impact in commit messages and PRs.
- Prefer minimal, focused PRs for each step.

---

## Deliverables
- Updated backend and frontend codebases with all improvements above.
- Automated tests for all permission logic.
- Updated and auto-generated documentation.
- Migration/usage guide for developers.

---

_Last updated: June 2025_
