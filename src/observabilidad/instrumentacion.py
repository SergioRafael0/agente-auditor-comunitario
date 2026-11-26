"""Instrumentacion de nodos del grafo y de las llamadas al LLM.

Dos mecanismos:

- `nodo_instrumentado`: decorador de nodos del grafo. Mide la latencia por
  paso, agrega `latencia_ms` a las entradas de `pasos_ejecutados` (viaja en
  el estado, trazable por paso) y registra el evento "nodo".
- `registrar_llamada_llm`: registra cada llamada al LLM (latencia, tokens
  reales de la API o estimados en modo demo, modelo, temperatura y modo
  real/demo/fallback_demo).
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, TypeVar

from src.observabilidad import trazas
from src.util.tokens import estimar_tokens

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., dict])


def nodo_instrumentado(nombre: str) -> Callable[[F], F]:
    """Decorador: mide latencia y exito de un nodo del grafo y lo registra."""

    def decorador(funcion: F) -> F:
        @wraps(funcion)
        def envoltorio(estado: dict) -> dict:
            trazas.activar_traza(estado.get("trace_id"), estado.get("thread_id"))
            inicio = time.time()
            try:
                resultado = funcion(estado)
            except Exception as e:
                trazas.registrar_evento(
                    "nodo",
                    nodo=nombre,
                    latencia_ms=_ms_desde(inicio),
                    ok=False,
                    error=f"{type(e).__name__}: {e}",
                )
                raise
            latencia_ms = _ms_desde(inicio)
            pasos = resultado.get("pasos_ejecutados") or []
            for paso in pasos:
                paso.setdefault("latencia_ms", latencia_ms)
            ok = all(p.get("ok", True) for p in pasos) if pasos else True
            trazas.registrar_evento("nodo", nodo=nombre, latencia_ms=latencia_ms, ok=ok)
            return resultado

        return envoltorio  # type: ignore[return-value]

    return decorador


def registrar_llamada_llm(
    rol: str,
    modelo: str,
    temperatura: float,
    inicio: float,
    modo: str,
    texto_entrada: str = "",
    texto_salida: str = "",
    tokens_entrada: int | None = None,
    tokens_salida: int | None = None,
    error: str | None = None,
) -> dict:
    """Registra una llamada al LLM con latencia y consumo de tokens.

    `modo`: "real" (API Groq), "demo" (simulada a proposito) o
    "fallback_demo" (la API fallo y se degrado a simulacion). Los tokens
    reales vienen del uso que reporta la API; en modo simulado se estiman
    y el evento lo marca en `tokens_estimados`.
    """
    estimados = tokens_entrada is None or tokens_salida is None
    if tokens_entrada is None:
        tokens_entrada = estimar_tokens(texto_entrada)
    if tokens_salida is None:
        tokens_salida = estimar_tokens(texto_salida)
    evento = {
        "rol": rol,
        "modelo": modelo,
        "temperatura": temperatura,
        "modo": modo,
        "ok": modo != "fallback_demo",
        "degradada": modo == "fallback_demo",
        "latencia_ms": _ms_desde(inicio),
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "tokens_estimados": estimados,
    }
    if error:
        evento["error"] = error
    return trazas.registrar_evento("llm_llamada", **evento)


def _ms_desde(inicio: float) -> int:
    return int((time.time() - inicio) * 1000)
