---
applyTo: '**'
---
Coding standards, domain knowledge, and preferences that AI should follow.

-- Please do not stop until the plan is fully implemented: Always complete the entire plan or task without leaving it unfinished. If you encounter an issue, document it and continue with the next steps.

-- Tanstack Router: Use Tanstack Router for all new routing logic in frontend projects. Prefer idiomatic usage and keep routes modular.

-- Always Apply changes you suggest: When suggesting improvements or refactors, always implement the changes directly in the codebase.

-- Vite, Tailwind, React, Typescript: All new frontend code should use Vite as the build tool, Tailwind CSS for styling, React for UI, and Typescript for type safety. Follow best practices for each technology.

-- RESTful Conventions: All backend APIs must follow RESTful conventions. Use clear and consistent resource naming, HTTP methods (GET, POST, PUT, PATCH, DELETE), and appropriate status codes. Avoid RPC-style endpoints. Document all endpoints clearly.

-- You are able to run the front end using `pnpm run dev`` in the frontend_app directory. However, Run only once and then create your summary if you are done. 
-- Do not and try and run the backend, its all deployed to the cloud but do not do that either.


-- Revamp Plan Stepwise Execution: When a revamp plan or migration is present (such as for the permission system, config, or cache), always:
  1. Follow the plan step by step, starting with foundational models and configuration files.
  2. Implement new modules (e.g., permissions enums, settings/config, unified cache) before refactoring existing code.
  3. Refactor existing code to use new modules incrementally, ensuring backwards compatibility.
  4. Remove legacy or duplicate code only after all usages are migrated.
  5. Add or update tests and documentation as you go.
  6. Communicate each step and its impact in commit messages and PR descriptions.
  7. Prefer minimal, focused PRs for each step to ease review and rollback if needed.