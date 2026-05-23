from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise exc


def mount_frontend(app: FastAPI) -> bool:
    if not FRONTEND_DIST.is_dir():
        return False

    @app.get("/app", include_in_schema=False)
    async def app_redirect():
        return RedirectResponse(url="/app/", status_code=307)

    app.mount(
        "/app",
        SPAStaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )
    return True
