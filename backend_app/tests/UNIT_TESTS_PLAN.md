# Unit Tests Plan

This document enumerates the unit tests I will create for the backend changes (permission deps, cached accessors, and router edits). For each test I list the target file, test function name, a short description, required fixtures/mocks, expected assertions, and important edge cases.

> Test runner: pytest (prefer minimal scope; use `pytest -q backend_app/tests/<file>`). Use `pytest --maxfail=1 -q` in CI for quick feedback.

---

## Goals / success criteria
- Verify permission dependency factories correctly allow/deny requests for owner, admin, and capability-holders.
- Ensure `get_effective_capabilities` merges base+custom capability maps correctly.
- Confirm job-scoped dependencies load the job and short-circuit unauthorized access.
- Validate route handlers that were converted to dependencies still perform expected work when authorized and reject when not.
- Keep tests small, deterministic, and fast by mocking external services (Cosmos, Storage, Analytics, Export).

---

## Fixtures (shared)
- `fake_user`: simple dict or Pydantic model with `id`, `permission_level`, and `custom_permissions`.
- `fake_job`: dict with `id`, `owner_id`, `status`, `metadata`.
- `mock_cosmos_service`: a mock for `services.cosmos_service` methods such as `get_job_by_id`, `query_jobs_for_user`.
- `mock_storage_service`: mock for `storage_service` used by download/export endpoints.
- `capability_map`: a dict mapping `PermissionCapability` keys to bool.
- `app_client`: FastAPI TestClient configured with dependency overrides for `get_current_user`, cosmos/storage services (for route-level tests).

Use `pytest` fixtures in `conftest.py` (under `backend_app/tests/conftest.py`) to provide common mocks and the `TestClient` builder.

---

## 1) Core dependency unit tests (fast, isolated)
Location: `backend_app/tests/test_dependencies.py`

- test_get_effective_capabilities_merges_base_and_custom
  - Description: Given base permissions and custom grants/revokes, returns merged map with overrides applied.
  - Fixtures/mocks: call function directly with sample inputs.
  - Assertions: resulting booleans match expected override semantics; unchanged capabilities preserved.
  - Edge cases: empty custom map, unknown capability keys (ignored), custom removes a capability.

- test_require_capability_allows_with_capability
  - Description: `require_capability` returns current_user when user has capability.
  - Mocks: stub `get_user_capabilities` to return map with a capability True.
  - Assertions: no HTTPException raised (call the dependency directly or via `Depends` helper using `asyncio` event loop).

- test_require_capability_denies_without_capability
  - Description: assert a 403-like error (HTTPException) when missing capability.
  - Mocks: stub `get_user_capabilities` to return capability False.
  - Assertions: raised HTTPException with status_code 403.

- test_require_job_capability_owner_short_circuits
  - Description: job-scoped dependency allows owner even without global capability.
  - Mocks: job.owner_id == current_user.id; `user_has_capability_for_job` configured to False.
  - Assertions: dependency returns job dict and does not raise.

- test_require_job_capability_admin_short_circuits
  - Description: admin users bypass owner rules.
  - Mocks: current_user.permission_level == ADMIN.
  - Assertions: dependency returns job dict.

- test_require_job_capability_denies_when_not_owner_or_cap
  - Description: non-owner without capability -> raises 403.
  - Mocks: job.owner_id != user.id and capability False.
  - Assertions: raises HTTPException(403).

---

## 2) Permissions module tests
Location: `backend_app/tests/test_permissions.py`

- test_get_user_capabilities_from_permission_level
  - Description: ensure PermissionLevel -> capabilities mapping matches `PERMISSION_CAPABILITIES`.
  - Assertions: all expected capabilities True for ADMIN, etc.

- test_merge_custom_capabilities_override
  - Description: merging custom rules permits and denies appropriately.
  - Edge: conflicting rules; ensure last-write or explicit precedence is documented and tested.

- test_user_has_capability_for_job_considers_owner_and_shared_flags
  - Description: user_has_capability_for_job should return True for owner or for shared with a capability.

---

## 3) Router-level unit tests (use TestClient, dependency overrides)
Location: `backend_app/tests/test_routers_<area>.py` (split by area)

### Document processing routes
File: `backend_app/tests/test_routers_document_processing.py`

- test_refine_analysis_requires_edit
  - Arrange: override `get_current_user` with non-editor user; `get_job_by_id` returns job owned by someone else.
  - Call: POST/PUT to the refine-analysis route (use TestClient).
  - Expect: 403 response when user lacks edit rights; 200 or 202 when user is owner/editor.
  - Mocks: mock analysis_service.process_refine to ensure it's called when allowed.

- test_generate_talking_points_allowed_for_editor_or_owner
  - Similar structure: ensure service called and returns expected payload.

- test_get_talking_points_view_permission
  - Ensure READ-capable users and owners can GET, others cannot.

- test_export_job_content_requires_export_capability
  - Mocks: ExportService.export_job called only when require_job_export dependency allows.
  - Assertions: unauthorized users receive 403; authorized users return 200 and content-type/attachment headers.

- test_download_original_file_requires_download_capability
  - Mocks: StorageService.get_blob_stream to return bytes-like; assert proper streaming response and status code 200 when allowed.

### Job management routes
File: `backend_app/tests/test_routers_job_management.py`

- test_get_jobs_honors_get_effective_capabilities
  - Setup: override `get_effective_capabilities` to return can_view_all True/False and validate returned job list shape.
  - Assertions: query to cosmos_service should include owner filter when can_view_all False.

- test_archive_restore_requires_owner_or_admin
  - Call archive endpoint for non-owner non-admin returns 403; admin/owner returns 200 and calls cosmos_service.update_job.

### File upload route
File: `backend_app/tests/test_routers_file_upload.py`

- test_upload_requires_upload_capability
  - Mocks: form file object; when `require_can_upload` denies, expect 403.
  - When allowed, ensure StorageService.upload_blob is called and response contains created job id or metadata.

---

## 4) Small integration-like unit tests (mocked services, end-to-end in memory)
Location: `backend_app/tests/test_end_to_end_snippets.py`

- test_full_flow_create_job_process_refine_export
  - Use TestClient with all external services mocked to deterministic returns.
  - Walk: create job (if API exposes), upload file, process analysis, export results.
  - Purpose: ensure the dependency wiring + service calls sequence holds together.

---

## 5) Edge cases & negative tests (important)
- Missing job id or job not found -> endpoints should return 404.
- Services raising unexpected exceptions -> dependency should raise 500 or bubble up and be caught by global handler.
- Slow external service simulated via mock raising Timeout -> ensure endpoint handles correctly (if code has timeouts).
- Capability maps missing keys -> default to False.

---

## 6) Test implementation notes & helpers
- Use `pytest-mock` or `unittest.mock` for patching imports such as `from app.services import cosmos_service`.
- Keep tests fast: no real network or DB calls.
- Put integration-like tests behind a `@pytest.mark.slow` marker if they spin up heavier setups.
- Add `conftest.py` fixtures:
  - `override_get_current_user(client, user)` helper that sets `app.dependency_overrides[get_current_user] = lambda: user`.
  - `mock_service(monkeypatch, module_path, function_name, return_value)` helper.

---

## 7) Test file map (what I'll create)
- `backend_app/tests/conftest.py` - shared fixtures / TestClient builder.
- `backend_app/tests/test_dependencies.py` - dependency-unit tests.
- `backend_app/tests/test_permissions.py` - permission logic tests.
- `backend_app/tests/test_routers_document_processing.py` - document-processing route tests.
- `backend_app/tests/test_routers_job_management.py` - job-management route tests.
- `backend_app/tests/test_routers_file_upload.py` - upload route tests.
- `backend_app/tests/test_end_to_end_snippets.py` - a couple of mocked end-to-end flows.

---

## 8) How to run
Run a focused test file:

```powershell
# from repo root
pytest -q backend_app/tests/test_dependencies.py
```

Run all backend tests:

```powershell
pytest -q backend_app/tests
```

---

## 9) Prioritization (first 3 to implement)
1. `test_dependencies.py` (core behavior)  
2. `test_permissions.py` (mapping correctness)  
3. `test_routers_document_processing.py` (critical API paths converted to dependencies)


---

## Appendix: Example test signature (to copy into files)
```python
def test_require_job_capability_owner_short_circuits(monkeypatch, fake_user, fake_job):
    # arrange: override get_current_user, mock cosmos.get_job_by_id -> fake_job
    # act: call require_job_capability(dep for edit) directly / via TestClient
    # assert: returns job and does not raise
    pass
```


End of plan.
