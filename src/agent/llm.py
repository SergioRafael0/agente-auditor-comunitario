"""Cliente Groq para el LLM, con modo demo sin API key."""

from __future__ import annotations

import logging
import os

from groq import Groq

from src.agent.respuestas_demo import simular

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


def generar(system: str, user: str, modelo: str | None = None, temperatura: float | None = None) -> str:
    """Llama al LLM con system + user y devuelve el texto de respuesta.

    En modo demo devuelve respuestas simuladas (basadas en corridas reales
    del sistema) en vez de consumir la API de Groq. Si la API falla a mitad
    de camino (clave invalida, sin conexion), degrada a la simulacion.
    """
    global _se_uso_demo
    if modo_demo():
        _se_uso_demo = True
        return simular(system, user)
    try:
        cli = cliente()
        response = cli.chat.completions.create(
            model=modelo or modelo_default(),
            temperature=temperatura if temperatura is not None else temperatura_default(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning("LLM no disponible (%s). Uso respuesta de demostracion.", e)
        _se_uso_demo = True
        return simular(system, user)
