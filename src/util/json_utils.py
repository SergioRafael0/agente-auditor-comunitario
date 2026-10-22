"""Extraccion robusta de JSON desde respuestas de LLM."""

from __future__ import annotations

import json
import re


def extraer_json(raw: str) -> dict:
    """Extrae el primer objeto JSON de una respuesta de LLM.

    Tolera los errores tipicos: bloques de codigo markdown (```json ... ```),
    texto explicativo alrededor del objeto, y llaves anidadas.
    Lanza json.JSONDecodeError si no encuentra ningun objeto parseable.
    """
    if not raw or not raw.strip():
        raise json.JSONDecodeError(" respuesta vacia", raw or "", 0)

    sin_fences = re.sub(r"```[a-zA-Z]*", "", raw).strip()
    try:
        data = json.loads(sin_fences)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    inicio = sin_fences.find("{")
    fin = sin_fences.rfind("}")
    if inicio != -1 and fin > inicio:
        candidato = sin_fences[inicio : fin + 1]
        data = json.loads(candidato)
        if isinstance(data, dict):
            return data
        raise json.JSONDecodeError("el contenido no es un objeto", candidato, 0)
    raise json.JSONDecodeError("sin objeto JSON en la respuesta", sin_fences, 0)
