"""LLM-as-judge offline: evalua calidad de las auditorias registradas."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agent.llm import generar

load_dotenv()

JUDGE_SYSTEM = """Eres un evaluador de calidad de un sistema RAG legal chileno.

Recibes:
- La publicacion original
- Los chunks de normativa que el sistema recupero
- La respuesta que dio el agente

Tu tarea: evaluar 3 cosas en formato JSON:
1. relevancia_chunks: ¿los chunks recuperados son relevantes a la publicacion? (0.0 a 1.0)
2. fundamentacion: ¿la respuesta se basa en los chunks o inventa? (0.0 a 1.0)
3. completitud: ¿falta normativa importante que deberia haberse mencionado? (0.0 a 1.0, donde 1.0 = nada falta)

Responde SOLO el JSON."""


def evaluar_registro(registro: dict) -> dict:
    """Evalua un registro de interaccion. Devuelve dict con scores."""
    chunks_texto = "\n\n".join(
        f"[{c.get('fuente','')} - {c.get('articulo','')}]" for c in registro.get("fragmentos_recuperados", [])
    )
    respuesta = json.dumps(registro.get("respuesta", {}), ensure_ascii=False)
    user = (
        f"Publicacion: {registro['input']['texto']}\n"
        f"Categoria: {registro['input']['categoria']}\n\n"
        f"Chunks recuperados:\n{chunks_texto or '(sin chunks)'}\n\n"
        f"Respuesta del agente:\n{respuesta}\n\n"
        "Evalua y devuelve el JSON pedido."
    )
    raw = generar(JUDGE_SYSTEM, user, temperatura=0.0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"relevancia_chunks": None, "fundamentacion": None, "completitud": None, "raw": raw[:200]}


def evaluar_todos(ruta_log: str | None = None, limite: int = 50) -> list[dict]:
    """Evalua los ultimos N registros del log de interacciones."""
    ruta = Path(ruta_log or os.getenv("LOG_FILE", "data/interacciones.jsonl"))
    if not ruta.exists():
        return []
    registros = [json.loads(line) for line in ruta.read_text(encoding="utf-8").splitlines() if line.strip()]
    registros = registros[-limite:]
    resultados = []
    for reg in registros:
        scores = evaluar_registro(reg)
        resultados.append({"interaccion_id": reg.get("interaccion_id"), "scores": scores})
    return resultados


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluar calidad del auditor con LLM-as-judge.")
    parser.add_argument("--limite", type=int, default=20)
    args = parser.parse_args()

    resultados = evaluar_todos(limite=args.limite)
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
