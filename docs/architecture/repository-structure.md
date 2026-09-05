# Repository structure

`backend/app/api` is composition/HTTP, `services` application use cases, `queries` persistence reads, `models` SQLAlchemy registration, `mqtt` external integration and `jobs` scheduled adapters. Refactor toward domain packages incrementally, preserving one model registry and compatibility imports.

Frontend is `app -> pages -> widgets -> features -> entities -> shared`. Infrastructure lives in `infra`; operational and decision records live in `docs`.
