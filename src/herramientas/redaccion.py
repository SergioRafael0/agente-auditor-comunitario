"""Tool de escritura: redacta informes, correcciones y respuestas normativas."""

from __future__ import annotations

import json
import logging

from src.agent.llm import generar
from src.herramientas.prompts import SYSTEM_REDACCION, user_redaccion
from src.util.json_utils import extraer_json

logger = logging.getLogger(__name__)


def redactar(
    modo: str,
    texto: str,
    categoria: str = "general",
    auditoria: dict | None = None,
    fragmentos: list[dict] | None = None,
    experiencias: list[dict] | None = None,
) -> dict:
    """Redacta un texto segun el modo y devuelve un dict estructurado.

    Modos validos: informe_auditoria | proponer_revision | respuesta_consulta.
    Si el LLM no devuelve JSON valido, se devuelve un dict de respaldo
    para que el grafo pueda continuar sin romperse.
    """
    if modo not in ("informe_auditoria", "proponer_revision", "respuesta_consulta"):
        raise ValueError(f"Modo de redaccion invalido: {modo}")

    user = user_redaccion(
        modo=modo,
        texto=texto,
        categoria=categoria,
        auditoria=auditoria,
        fragmentos=fragmentos,
        experiencias=experiencias,
    )
    raw = generar(system=SYSTEM_REDACCION, user=user, temperatura=0.2)

    try:
        data = extraer_json(raw)
    except json.JSONDecodeError:
        logger.warning("Redaccion: LLM no devolvio JSON valido. Raw: %s", raw[:200])
        data = {}
    return {
        "modo": modo,
        "titulo": str(data.get("titulo", "")),
        "cuerpo": str(data.get("cuerpo", "")),
        "acciones": list(data.get("acciones", [])),
    }
