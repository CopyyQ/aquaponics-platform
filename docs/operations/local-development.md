# Local development

Copy `.env.example` files, run `docker compose config --quiet`, then `docker compose up --build`. API is 8000, frontend 3000 and MQTT 1883. MQTT is anonymous controlled-LAN development traffic only; do not expose it publicly. Run Alembic before seed and use documented validation targets.

Before starting, replace `SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` in `backend/.env` with your own values. The bootstrap admin password is required through environment configuration; keep local `.env` files out of Git.
