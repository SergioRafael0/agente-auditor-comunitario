"""Estado compartido del grafo del agente (LangGraph StateGraph)."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

PASOS_VALIDOS = (
    "memoria",
    "consulta_normativa",
    "auditoria",
    "redaccion",
    "guardar_memoria",
)

MAX_ITERACIONES = 12
MAX_INTENTOS_POR_PASO = 2


class EstadoAgente(TypedDict, total=False):
    publicacion: str
    categoria: str
    tipo_tarea: str
    plan: list[dict]
    indice_paso: int
    nodo_siguiente: str | None
    iteraciones: int
    pasos_ejecutados: Annotated[list[dict], operator.add]
    bitacora: Annotated[list[dict], operator.add]
    errores: Annotated[list[dict], operator.add]
    experiencias_previas: list[dict]
    fragmentos_normativos: list[dict]
    auditoria: dict | None
    redaccion: dict | None
    respuesta_final: str | None
    historial: Annotated[list[dict], operator.add]


def intentos_de(pasos_ejecutados: list[dict], paso: str) -> int:
    """Cuenta cuantas veces se ejecuto (ok o fallado) un paso del plan."""
    return sum(1 for e in pasos_ejecutados if e.get("paso") == paso)
