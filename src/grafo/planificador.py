"""Nodo planificador: descompone la tarea en pasos priorizados.

Usa el LLM para decidir el tipo de tarea y la secuencia de pasos
(toma de decisiones inicial). Si el LLM falla o devuelve un plan
invalido, aplica una heuristica deterministica como respaldo, de modo
que el agente nunca quede sin plan.
"""

from __future__ import annotations

import json
import logging
import re

from src.agent.llm import generar
from src.grafo.estado import PASOS_VALIDOS
from src.util.json_utils import extraer_json

logger = logging.getLogger(__name__)

ALEATORIA_VAGA_MIN_LEN = 25

SYSTEM_PLANIFICADOR = """Eres el planificador de un agente de auditoria normativa para comunidades chilenas.

Te dan la publicacion y su categoria. Debes decidir:
1. tipo_tarea: "auditoria" (evaluar cumplimiento de una publicacion)
   o "consulta_normativa" (la usuario pregunta que exige la ley para algo).
2. Una lista de pasos ordenados por prioridad (1 = primero, mas prioridad).
   Nombres de pasos validos: memoria, consulta_normativa, auditoria, redaccion, guardar_memoria.

Significado de los pasos:
- memoria: recuperar experiencias previas similares (siempre conviene, prioridad 1).
- auditoria: someter la publicacion al auditor normativo (obligatorio en auditoria).
- consulta_normativa: buscar fragmentos legales en el indice RAG (obligatorio en consulta_normativa).
- redaccion: redactar el informe/respuesta final con la herramienta de escritura (siempre al final del analisis).
- guardar_memoria: persistir la experiencia para flujos futuros (solo si hubiese auditoria).

Si la publicacion es vaga o de categoria "general" sin detalle, NO necesitas consulta_normativa: el auditor detectara la vaguedad y el redactor propondra una revision.

Criterio estricto para tipo_tarea:
- Si describe un TRABAJO o necesidad concreta (instalar, arreglar, reparar, cambiar, pintar, construir, contratar...) -> SIEMPRE "auditoria", aunque mencione temas tecnicos.
- SOLO si es una PREGUNTA sobre que dice la ley/normativa (ej: "que exige la ley...", "cuales son los requisitos...?") -> "consulta_normativa".

Ejemplos:
- "Necesito instalar un porton electrico" -> tipo_tarea "auditoria".
- "Que exige la normativa SEC para un tablero electrico?" -> tipo_tarea "consulta_normativa".

Reglas:
1. Responde SOLO el JSON pedido.
2. Los pasos deben priorizarse de lo mas barato/informativo a lo costoso.
3. No incluyas pasos repetidos.

JSON de salida estricto:
{
  "tipo_tarea": "auditoria|consulta_normativa",
  "pasos": [
    {"nombre": "memoria", "prioridad": 1, "justificacion": "paso razon"},
    {"nombre": "...", "prioridad": 2, "justificacion": "..."}
  ]
}"""


def planificar(publicacion: str, categoria: str) -> tuple[str, list[dict]]:
    """Devuelve (tipo_tarea, plan). Plan priorizado con respaldo heuristico."""
    try:
        raw = generar(
            system=SYSTEM_PLANIFICADOR,
            user=f"Categoria: {categoria}\nPublicacion: {publicacion}",
            temperatura=0.0,
        )
        data = extraer_json(raw)
        tipo = data["tipo_tarea"]
        if tipo not in ("auditoria", "consulta_normativa"):
            raise ValueError(f"tipo_tarea invalido: {tipo}")
        plan = _validar_plan(data["pasos"])
        return tipo, plan
    except Exception as e:
        logger.warning("Planificador: LLM fallo (%s). Uso heuristica deterministica.", type(e).__name__)
        return _plan_heuristico(publicacion, categoria)


def _validar_plan(pasos: list) -> list[dict]:
    if not isinstance(pasos, list) or not pasos:
        raise ValueError("plan vacio")
    limpio: list[dict] = []
    for p in pasos:
        nombre = str(p.get("nombre", "")).strip()
        if nombre not in PASOS_VALIDOS:
            raise ValueError(f"paso invalido: {nombre}")
        if any(e["nombre"] == nombre for e in limpio):
            continue
        limpio.append(
            {
                "nombre": nombre,
                "prioridad": int(p.get("prioridad", 99)),
                "justificacion": str(p.get("justificacion", "")),
            }
        )
    if not limpio:
        raise ValueError("plan sin pasos validos")
    limpio.sort(key=lambda e: e["prioridad"])
    return limpio


def _plan_heuristico(publicacion: str, categoria: str) -> tuple[str, list[dict]]:
    es_consulta = _parece_consulta_normativa(publicacion)
    if es_consulta:
        return "consulta_normativa", [
            {"nombre": "memoria", "prioridad": 1, "justificacion": "experiencias previas similares"},
            {"nombre": "consulta_normativa", "prioridad": 2, "justificacion": "se pregunta por normativa"},
            {"nombre": "redaccion", "prioridad": 3, "justificacion": "redactar respuesta fundada"},
        ]
    es_vaga = len(publicacion.strip()) < ALEATORIA_VAGA_MIN_LEN or categoria == "general"
    plan = [
        {"nombre": "memoria", "prioridad": 1, "justificacion": "experiencias previas similares"},
        {"nombre": "auditoria", "prioridad": 2, "justificacion": "evaluar cumplimiento normativo"},
        {"nombre": "redaccion", "prioridad": 3, "justificacion": "informe o revision de la publicacion"},
        {"nombre": "guardar_memoria", "prioridad": 4, "justificacion": "persistir experiencia"},
    ]
    if es_vaga:
        plan[2]["justificacion"] = "publicacion vaga: proponer publicacion corregida"
    return "auditoria", plan


def _parece_consulta_normativa(publicacion: str) -> bool:
    patrones = r"\?|\b(cuales?|que|como)\b.*\b(exige|requiere|pide|normativ\w+|ley|articulo|regla)\b"
    return bool(re.search(patrones, publicacion.lower(), re.IGNORECASE))
