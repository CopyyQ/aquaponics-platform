# Frontend permission migration

The API exposes `GET /auth/session` with the authenticated user and effective database permission codes. Frontend migration should hydrate this response once per session and gate controls with permission codes; role-name checks are compatibility-only and must not be used as a security boundary. The backend remains authoritative for every operation.
