# Naming conventions

Python files/functions are snake_case; models/schemas/classes PascalCase; constants UPPER_SNAKE_CASE. Use `EntityCreate`, `EntityUpdate`, `EntityResponse/Read` consistently and responsibility-specific modules such as `project_access_service.py`.

React components/pages use PascalCase, hooks `useXxx.ts`, API/utilities kebab-case, schemas `*.schema.ts`, tests `*.test.ts(x)`. User-facing labels are Vietnamese. Lifecycle uses `is_enabled`; connectivity uses `WAITING_CONNECTION`, `ONLINE`, `OFFLINE`.
