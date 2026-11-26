"""Cliente Groq para el LLM, con modo demo sin API key.

Observabilidad y resiliencia (Evaluacion 3):
- Cada llamada se registra como evento "llm_llamada" (latencia, tokens reales
  de la API o estimados en demo, modelo y modo real/demo/fallback_demo).
- Modelo y max_tokens configurables por rol (GROQ_MODEL_<ROL>,
  GROQ_MAX_TOKENS_<ROL>): el planificador puede usar un modelo mas liviano
  que el auditor, segun criticidad.
- Ante rate limit (429) reintenta con backoff exponencial (LLM_REINTENTOS,
  LLM_BACKOFF_S) y solo degrada a la simulacion si los reintentos fallan.
"""

from __future__ import annotations

import logging
import os
import time

from groq import Groq

from src.agent.respuestas_demo import simular
from src.observabilidad import trazas
from src.observabilidad.instrumentacion import registrar_llamada_llm

logger = logging.getLogger(__name__)

_demo_forzado = False
_se_uso_demo = False

MAX_TOKENS_POR_ROL = {
    "planificador": 2000,
    "auditor": 3000,
    "redaccion": 3000,
    "judge": 1000,
}
# Nota: los modelos gpt-oss son de razonamiento y sus tokens de razonamiento
# cuentan dentro de max_completion_tokens: un tope bajo trunca el JSON visible.
# Estos limites son una cota de seguridad contra salidas desbocadas, no una
# herramienta de recorte.


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


def modelo_para_rol(rol: str) -> str:
    """Modelo por rol (GROQ_MODEL_<ROL>); por defecto el modelo general."""
    configurado = os.getenv(f"GROQ_MODEL_{rol.upper()}", "").strip()
    return configurado or modelo_default()


def max_tokens_para_rol(rol: str) -> int:
    """Tope de tokens de salida por rol (GROQ_MAX_TOKENS_<ROL>)."""
    configurado = os.getenv(f"GROQ_MAX_TOKENS_{rol.upper()}", "").strip()
    if configurado:
        return int(configurado)
    return MAX_TOKENS_POR_ROL.get(rol, 1024)


def temperatura_default() -> float:
    return float(os.getenv("GROQ_TEMPERATURE", "0.2"))


def es_rate_limit(error: Exception) -> bool:
    """True si el error es un rate limit (429) de la API."""
    nombre = type(error).__name__.lower()
    texto = str(error).lower()
    return "ratelimit" in nombre or "429" in texto or "rate_limit" in texto


def generar(
    system: str,
    user: str,
    modelo: str | None = None,
    temperatura: float | None = None,
    rol: str = "llm",
    max_tokens: int | None = None,
) -> str:
    """Llama al LLM con system + user y devuelve el texto de respuesta.

    En modo demo devuelve respuestas simuladas (basadas en corridas reales
    del sistema) en vez de consumir la API de Groq. Si la API falla a mitad
    de camino (clave invalida, sin conexion), degrada a la simulacion; los
    rate limits (429) se reintentan con backoff antes de degradar.
    """
    global _se_uso_demo
    modelo_usado = modelo or modelo_para_rol(rol)
    temp = temperatura if temperatura is not None else temperatura_default()
    limite = max_tokens if max_tokens is not None else max_tokens_para_rol(rol)
    reintentos = int(os.getenv("LLM_REINTENTOS", "2"))
    backoff = float(os.getenv("LLM_BACKOFF_S", "20"))
    inicio = time.time()

    if modo_demo():
        _se_uso_demo = True
        texto = simular(system, user)
        registrar_llamada_llm(
            rol, modelo_usado, temp, inicio, modo="demo",
            texto_entrada=system + user, texto_salida=texto,
        )
        return texto

    error: Exception | None = None
    for intento in range(reintentos + 1):
        try:
            cli = cliente()
            response = cli.chat.completions.create(
                model=modelo_usado,
                temperature=temp,
                max_completion_tokens=limite,
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
            error = e
            if es_rate_limit(e) and intento < reintentos:
                espera = backoff * (2 ** intento)
                trazas.registrar_evento(
                    "llm_reintento",
                    rol=rol,
                    modelo=modelo_usado,
                    intento=intento + 1,
                    espera_s=espera,
                    error=f"{type(e).__name__}: {e}",
                )
                logger.warning(
                    "Rate limit en llamada LLM (rol %s): reintento %d en %.0f s.",
                    rol, intento + 1, espera,
                )
                time.sleep(espera)
                continue
            break

    logger.warning("LLM no disponible (%s). Uso respuesta de demostracion.", error)
    _se_uso_demo = True
    texto = simular(system, user)
    registrar_llamada_llm(
        rol, modelo_usado, temp, inicio, modo="fallback_demo",
        texto_entrada=system + user, texto_salida=texto,
        error=f"{type(error).__name__}: {error}",
    )
    return texto
