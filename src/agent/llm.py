"""Cliente Groq para el LLM, con modo demo sin API key."""

from __future__ import annotations

import logging
import os
import time

from groq import Groq

from src.agent.respuestas_demo import simular
from src.observabilidad.instrumentacion import registrar_llamada_llm

logger = logging.getLogger(__name__)

_demo_forzado = False
_se_uso_demo = False


def activar_modo_demo() -> None:
    """Fuerza el modo demo (flag --demo de la CLI)."""
    global _demo_forzado
    _demo_forzado = True


def modo_demo() -> bool:
    """True si el LLM debe simularse: --demo, LLM_MODO=offline o sin API key."""
    if _demo_forzado:
        return True
    if os.getenv("LLM_MODO", "").strip().lower() in ("offline", "demo"):
        return True
    return not os.getenv("GROQ_API_KEY", "").strip()


def se_uso_demo() -> bool:
    """True si alguna llamada fue respondida con la simulacion."""
    return _se_uso_demo


def cliente() -> Groq:
    """Devuelve un cliente Groq configurado."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no esta definida en .env")
    return Groq(api_key=api_key)


def modelo_default() -> str:
    return os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def temperatura_default() -> float:
    return float(os.getenv("GROQ_TEMPERATURE", "0.2"))


def generar(
    system: str,
    user: str,
    modelo: str | None = None,
    temperatura: float | None = None,
    rol: str = "llm",
) -> str:
    """Llama al LLM con system + user y devuelve el texto de respuesta.

    En modo demo devuelve respuestas simuladas (basadas en corridas reales
    del sistema) en vez de consumir la API de Groq. Si la API falla a mitad
    de camino (clave invalida, sin conexion), degrada a la simulacion.

    Cada llamada queda registrada como evento "llm_llamada" (latencia,
    tokens, modelo y modo real/demo/fallback_demo) en data/eventos.jsonl.
    `rol` identifica al consumidor (planificador, auditor, redaccion, judge)
    para las metricas por tipo de llamada.
    """
    global _se_uso_demo
    modelo_usado = modelo or modelo_default()
    temp = temperatura if temperatura is not None else temperatura_default()
    inicio = time.time()

    if modo_demo():
        _se_uso_demo = True
        texto = simular(system, user)
        registrar_llamada_llm(
            rol, modelo_usado, temp, inicio, modo="demo",
            texto_entrada=system + user, texto_salida=texto,
        )
        return texto
    try:
        cli = cliente()
        response = cli.chat.completions.create(
            model=modelo_usado,
            temperature=temp,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        texto = response.choices[0].message.content or ""
        uso = getattr(response, "usage", None)
        registrar_llamada_llm(
            rol, modelo_usado, temp, inicio, modo="real",
            texto_entrada=system + user, texto_salida=texto,
            tokens_entrada=getattr(uso, "prompt_tokens", None),
            tokens_salida=getattr(uso, "completion_tokens", None),
        )
        return texto
    except Exception as e:
        logger.warning("LLM no disponible (%s). Uso respuesta de demostracion.", e)
        _se_uso_demo = True
        texto = simular(system, user)
        registrar_llamada_llm(
            rol, modelo_usado, temp, inicio, modo="fallback_demo",
            texto_entrada=system + user, texto_salida=texto,
            error=f"{type(e).__name__}: {e}",
        )
        return texto
