"""Cliente Groq para el LLM."""

from __future__ import annotations

import os

from groq import Groq


def cliente() -> Groq:
    """Devuelve un cliente Groq configurado."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no esta definida en .env")
    return Groq(api_key=api_key)


def modelo_default() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def temperatura_default() -> float:
    return float(os.getenv("GROQ_TEMPERATURE", "0.2"))


def generar(system: str, user: str, modelo: str | None = None, temperatura: float | None = None) -> str:
    """Llama al LLM con system + user y devuelve el texto de respuesta."""
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
