# Reitti

## Setup

1. Install tools: [Docker](https://docs.docker.com/get-docker/), [just](https://github.com/casey/just), [uv](https://docs.astral.sh/uv/), Node.js 20+ (`n lts` or `nvm install 22`).
2. Download and prepare data: `just setup`
3. Start containers: `just run`
4. Load the database: `just prepare-postgis`
5. Configure backend: copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL` and `GRAPHHOPPER_BASE_URL`.
6. Install and build the frontend:
   ```sh
   just frontend-install
   just frontend-build
   ```
7. Start the API (from `backend/`):
   ```sh
   just dev-server
   ```
8. Open the app at [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/).

After changing frontend code, run `just frontend-build` again (or `just frontend-build` from `backend/`).

For frontend-only development with hot reload: `cd frontend && just dev` (Vite at `/app/` on its own port).

## Name Origin

The name Reitti [ˈre̞i̯t̪ːi] is the Finnish word for "route", "path", or "track". It reflects the project's core identity, as the application is specifically designed for the city of Helsinki.
