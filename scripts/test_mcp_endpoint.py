"""Prueba el endpoint MCP via HTTP sin necesidad de Claude Desktop.

Lanza el server en un thread, hace una peticion JSON-RPC al endpoint /mcp,
y muestra la respuesta. Sirve como smoke test del server y como demo
de lo que haria Claude Desktop al conectarse.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv

from src.mcp_server.server import build_app

load_dotenv()


def parsear_respuesta(r: httpx.Response) -> dict | None:
    """Parsea la respuesta MCP, sea JSON o SSE (text/event-stream)."""
    content_type = r.headers.get("content-type", "")
    body = r.text
    if "text/event-stream" in content_type or body.startswith("event:"):
        for linea in body.splitlines():
            if linea.startswith("data:"):
                return json.loads(linea[len("data:"):].strip())
        return None
    try:
        return r.json()
    except Exception:
        return None

HOST = "127.0.0.1"
PORT = int(os.getenv("MCP_PORT", "8765"))  # uso 8765 para no chocar con apps del usuario
TOKEN = os.getenv("MCP_AUTH_TOKEN", "test-token")
URL = f"http://{HOST}:{PORT}/mcp"


def levantar_server() -> uvicorn.Server:
    config = uvicorn.Config(build_app(), host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(30):
        try:
            httpx.get(f"http://{HOST}:{PORT}/", timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)
    return server


def peticinicial() -> dict:
    """Handshake inicial del protocolo MCP: enviar initialize."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-script", "version": "0.1"},
        },
    }


def peticion_listar_tools(session_id: str | None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }


def peticion_llamar_tool() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "revisar_publicacion",
            "arguments": {
                "texto": "Necesito arreglar el ascensor del edificio que hace ruidos raros al subir",
                "categoria": "ascensor",
            },
        },
    }


def mostrar_respuesta(resp: dict) -> None:
    print(f"\nRespuesta JSON-RPC:")
    print(json.dumps(resp, indent=2, ensure_ascii=False))


def main() -> None:
    print(f"Levantando MCP server en {URL}...")
    server = levantar_server()
    print(f"  Server arriba (token={TOKEN[:8]}...)")

    try:
        with httpx.Client(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }

            print(f"\n[1/3] Enviando initialize...")
            r = client.post(URL, json=peticinicial(), headers=headers)
            print(f"  Status: {r.status_code}")
            if r.status_code != 200:
                print(f"  Body: {r.text[:500]}")
                return
            session_id = r.headers.get("mcp-session-id")
            if session_id:
                headers["mcp-session-id"] = session_id
                print(f"  Session ID: {session_id[:16]}...")

            data = parsear_respuesta(r)
            if data:
                mostrar_respuesta(data)
            else:
                print(f"  Body (no parseable): {r.text[:300]}")

            print(f"\n[2/3] Listando tools disponibles...")
            r = client.post(URL, json=peticion_listar_tools(session_id), headers=headers)
            print(f"  Status: {r.status_code}")
            data = parsear_respuesta(r)
            if data and "result" in data and "tools" in data["result"]:
                tools = [t["name"] for t in data["result"]["tools"]]
                print(f"  Tools: {tools}")
            elif data:
                mostrar_respuesta(data)
            else:
                print(f"  Body: {r.text[:500]}")

            print(f"\n[3/3] Llamando revisar_publicacion con un caso real...")
            r = client.post(URL, json=peticion_llamar_tool(), headers=headers)
            print(f"  Status: {r.status_code}")
            data = parsear_respuesta(r)
            if data and "result" in data and "content" in data["result"]:
                texto = "".join(
                    c.get("text", "") for c in data["result"]["content"] if isinstance(c, dict)
                )
                resultado = json.loads(texto)
                print(f"\n  Estado: {resultado.get('estado')}")
                print(f"  Alertas: {len(resultado.get('alertas', []))}")
                for alerta in resultado.get("alertas", []):
                    print(f"    - {alerta.get('fuente')} {alerta.get('articulo')}: {alerta.get('mensaje', '')[:100]}")
                print(f"  Fragmentos recuperados: {len(resultado.get('fragmentos_recuperados', []))}")
                print(f"  Latencia: {resultado.get('latencia_ms')}ms")

                output_path = Path("data/eval/mcp_endpoint_demo.json")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(resultado, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"\n  Output completo guardado en {output_path}")
            elif data:
                mostrar_respuesta(data)
            else:
                print(f"  Body: {r.text[:500]}")
    finally:
        print(f"\nBajando server...")
        server.should_exit = True
        time.sleep(0.5)
        print(f"  Server bajado.")


if __name__ == "__main__":
    main()
