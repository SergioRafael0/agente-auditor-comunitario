"""Trazas y eventos estructurados de observabilidad.

Cada ejecucion del agente recibe un `trace_id` que correlaciona los eventos
granulares (llamadas al LLM, nodos del grafo) con la interaccion de la tool
(`data/interacciones.jsonl`) y la ejecucion completa del grafo
(`data/agente_ejecuciones.jsonl`).

Los eventos se persisten uno por linea en `data/eventos.jsonl` (ruta
configurable con `LOG_FILE_EVENTOS`; con la variable vacia no se persisten).
Esquema base de un evento:

    {
      "evento": "llm_llamada" | "nodo" | "fallback",
      "trace_id": "...", "thread_id": "...", "timestamp": "ISO-8601 UTC",
      ... campos especificos del tipo de evento
    }
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

logger = logging.getLogger(__name__)

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_thread_id: ContextVar[str | None] = ContextVar("thread_id", default=None)

_eventos: list[dict] = []


def nueva_traza(thread_id: str | None = None) -> str:
    """Inicia una traza nueva y la activa en el contexto actual."""
    return activar_traza(str(uuid.uuid4()), thread_id or str(uuid.uuid4()))


def activar_traza(trace_id: str | None, thread_id: str | None = None) -> str:
    """Activa una traza (creando el id que falte) y la fija en el contexto."""
    tid = trace_id or str(uuid.uuid4())
    _trace_id.set(tid)
    if thread_id:
        _thread_id.set(thread_id)
    return tid


def asegurar_traza() -> str:
    """Devuelve el trace_id activo; si no hay traza, inicia una nueva."""
    actual = _trace_id.get()
    return actual if actual else nueva_traza()


def trace_id() -> str | None:
    return _trace_id.get()


def thread_id() -> str | None:
    return _thread_id.get()


def registrar_evento(tipo: str, **campos) -> dict:
    """Registra un evento estructurado: al buffer y a data/eventos.jsonl."""
    evento = {
        "evento": tipo,
        "trace_id": _trace_id.get(),
        "thread_id": _thread_id.get(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    evento.update(campos)
    _eventos.append(evento)
    _persistir(evento)
    return evento


def eventos_traza(trace_id: str | None = None) -> list[dict]:
    """Eventos registrados para una traza (por defecto, la activa)."""
    tid = trace_id or _trace_id.get()
    return [e for e in _eventos if e.get("trace_id") == tid]


def resumen_llm(trace_id: str | None = None) -> dict:
    """Agrega las llamadas al LLM de una traza: tokens, modos y latencias."""
    llamadas = [e for e in eventos_traza(trace_id) if e.get("evento") == "llm_llamada"]
    latencias = [e.get("latencia_ms", 0) for e in llamadas]
    return {
        "llamadas_llm": len(llamadas),
        "tokens_entrada": sum(e.get("tokens_entrada") or 0 for e in llamadas),
        "tokens_salida": sum(e.get("tokens_salida") or 0 for e in llamadas),
        "modos": sorted({e.get("modo") for e in llamadas if e.get("modo")}),
        "latencia_llm_ms": sum(latencias),
    }


def reiniciar() -> None:
    """Limpia el contexto y el buffer de eventos (tests y benchmarks largos)."""
    _trace_id.set(None)
    _thread_id.set(None)
    _eventos.clear()


def _persistir(evento: dict) -> None:
    ruta = os.getenv("LOG_FILE_EVENTOS", "data/eventos.jsonl")
    if not ruta:
        return
    try:
        p = Path(ruta)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("No se pudo persistir el evento de observabilidad: %s", e)
