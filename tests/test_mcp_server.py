"""Tests del MCP server (mockeando el agente)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from src.mcp_server import server


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "test-token")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_validar_auth_token_correcto():
    auth = server.AuthMiddleware()
    ok, motivo = auth.validar({"authorization": "Bearer test-token"})
    assert ok is True
    assert isinstance(motivo, str)


def test_validar_auth_token_incorrecto():
    auth = server.AuthMiddleware()
    ok, motivo = auth.validar({"authorization": "Bearer otro"})
    assert ok is False
    assert "invalido" in motivo.lower()


def test_validar_auth_sin_header():
    auth = server.AuthMiddleware()
    ok, motivo = auth.validar({})
    assert ok is False


def test_build_server_define_revisar_publicacion():
    mcp = server._build_server()
    tools = _run(mcp.list_tools())
    nombres = [t.name for t in tools]
    assert "revisar_publicacion" in nombres


def test_call_tool_revisar_publicacion_devuelve_json():
    respuesta = {
        "interaccion_id": "abc-123",
        "estado": "alerta",
        "alertas": [{"fuente": "SEC", "articulo": "X", "mensaje": "m", "recomendacion": "r"}],
        "recomendaciones_generales": [],
        "fragmentos_recuperados": [],
        "latencia_ms": 100,
    }
    with patch.object(server, "auditar_publicacion", return_value=respuesta):
        mcp = server._build_server()
        resultado = _run(
            mcp.call_tool("revisar_publicacion", {"texto": "arreglar porton", "categoria": "electricidad"})
        )
    if isinstance(resultado, tuple):
        contenido = resultado[0]
    else:
        contenido = resultado
    assert len(contenido) >= 1
    texto = "".join(b.text for b in contenido if hasattr(b, "text"))
    data = json.loads(texto)
    assert data["estado"] == "alerta"


def test_call_tool_desconocida_lanza_error():
    from mcp.server.fastmcp.exceptions import ToolError

    mcp = server._build_server()
    with pytest.raises(ToolError):
        _run(mcp.call_tool("herramienta_inexistente", {}))
