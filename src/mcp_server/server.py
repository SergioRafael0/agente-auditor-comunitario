"""MCP server con la tool revisar_publicacion (usando FastMCP)."""

from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.agent.auditor import auditar_publicacion
from src.mcp_server.auth import AuthMiddleware

load_dotenv()
logger = logging.getLogger(__name__)

INSTRUCTIONS = """Eres el Agente Auditor Comunitario (AAC). Tu unica funcion es auditar publicaciones
de la plataforma Proveedores & Comunidades contra normativa chilena (Ley 21.442 y SEC).

Cuando el usuario publique una descripcion de necesidad de mantenimiento o servicio para una
comunidad, USA la herramienta revisar_publicacion pasando la categoria apropiada y la
descripcion textual. Devuelve al usuario el estado, las alertas con su fuente legal y las
recomendaciones.

Categorias validas: electricidad, ascensor, gas, agua, general.
"""


def _build_server() -> FastMCP:
    mcp = FastMCP(
        name="agente-auditor-comunitario",
        instructions=INSTRUCTIONS,
    )

    @mcp.tool()
    def revisar_publicacion(texto: str, categoria: str = "general") -> str:
        """Audita una publicacion contra la Ley 21.442 de Copropiedad Inmobiliaria
        y normativa SEC chilena. Devuelve estado (cumple/alerta/no_cumple),
        alertas regulatorias con cita a la fuente legal, y recomendaciones.

        Args:
            texto: descripcion completa de la publicacion a auditar.
            categoria: categoria de la publicacion (electricidad, ascensor, gas, agua, general).
        """
        resultado = auditar_publicacion(texto, categoria)
        return json.dumps(resultado, ensure_ascii=False, indent=2)

    return mcp


mcp = _build_server()


def build_app():
    """Devuelve una app ASGI lista para uvicorn, con middleware de auth."""
    from starlette.middleware import Middleware
    from starlette.types import ASGIApp, Receive, Scope, Send

    app = mcp.streamable_http_app()
    auth = AuthMiddleware()

    class AuthMiddlewareASGI:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            from starlette.responses import JSONResponse

            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            ok, motivo = auth.validar(headers)
            if not ok:
                response = JSONResponse({"error": motivo}, status_code=401)
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)

    app.add_middleware(Middleware, dispatch=AuthMiddlewareASGI)  # type: ignore[arg-type]
    return app


app = build_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    uvicorn.run(app, host=host, port=port)
