"""Subagentes especializados (uno por nodo del grafo).

Cada subagente ejecuta UNA herramienta y actualiza el estado. Los errores
se registran en `errores` para que el enrutador pueda reintentar o
ajustar el plan (toma de decisiones adaptativa).
"""

from __future__ import annotations

import logging

from src.herramientas.consulta import buscar_normativa
from src.herramientas.redaccion import redactar
from src.herramientas.razonamiento import auditar
from src.memoria.largo_plazo import buscar_experiencias, guardar_experiencia

logger = logging.getLogger(__name__)


def nodo_memoria(estado: dict) -> dict:
    """Subagente de memoria: carga experiencias previas similares."""
    texto = estado.get("publicacion", "")
    try:
        experiencias = buscar_experiencias(texto, top_k=3)
        return {
            "experiencias_previas": experiencias,
            "pasos_ejecutados": [{"paso": "memoria", "ok": True}],
            "bitacora": [
                {
                    "nodo": "subagente_memoria",
                    "decision": f"Se recuperaron {len(experiencias)} experiencias previas.",
                }
            ],
        }
    except Exception as e:
        return _error_paso("memoria", e)


def nodo_consulta_normativa(estado: dict) -> dict:
    """Subagente de consulta: busca normativa en el indice RAG."""
    try:
        resultado = buscar_normativa(
            estado.get("publicacion", ""),
            categoria=estado.get("categoria") or None,
            top_k=5,
        )
        decision = (
            f"Se encontraron {resultado['n_fragmentos']} fragmentos"
            f" de {len(resultado['fuentes'])} fuentes."
        )
        return {
            "fragmentos_normativos": resultado["fragmentos"],
            "pasos_ejecutados": [{"paso": "consulta_normativa", "ok": True}],
            "bitacora": [{"nodo": "subagente_consulta", "decision": decision}],
        }
    except Exception as e:
        return _error_paso("consulta_normativa", e)


def nodo_auditoria(estado: dict) -> dict:
    """Subagente auditor: evalua la publicacion contra la normativa."""
    try:
        auditoria = auditar(estado.get("publicacion", ""), estado.get("categoria", "general"))
        decision = f"Veredicto del auditor: {auditoria['estado']} ({len(auditoria['alertas'])} alertas)."
        return {
            "auditoria": auditoria,
            "historial": [
                {
                    "publicacion": estado.get("publicacion", ""),
                    "categoria": estado.get("categoria", "general"),
                    "veredicto": auditoria["estado"],
                }
            ],
            "pasos_ejecutados": [{"paso": "auditoria", "ok": True}],
            "bitacora": [{"nodo": "subagente_auditor", "decision": decision}],
        }
    except Exception as e:
        return _error_paso("auditoria", e)


def nodo_redaccion(estado: dict) -> dict:
    """Subagente redactor: redacta la salida final segun el tipo de tarea.

    Decision adaptativa:
    - auditoria con veredicto vago (no_cumple sin alertas) -> proponer_revision.
    - auditoria normal -> informe_auditoria.
    - consulta normativa -> respuesta_consulta.
    - si la auditoria fallo dos veces -> informe de fallo sin LLM.
    """
    texto = estado.get("publicacion", "")
    categoria = estado.get("categoria", "general")
    auditoria = estado.get("auditoria")
    fallos_auditoria = sum(
        1 for e in estado.get("errores", []) if e.get("paso") == "auditoria"
    )

    try:
        if estado.get("tipo_tarea") == "consulta_normativa":
            resultado = redactar(
                modo="respuesta_consulta",
                texto=texto,
                categoria=categoria,
                fragmentos=estado.get("fragmentos_normativos") or [],
                experiencias=estado.get("experiencias_previas") or [],
            )
            decision = "Consulta normativa respondida con citas del RAG."
        elif auditoria is None:
            resultado = {
                "modo": "informe_auditoria",
                "titulo": "Auditoria no disponible",
                "cuerpo": (
                    "El auditor no pudo generar un veredicto en esta ejecucion."
                    " Revisa los errores registrados y reintenta."
                ),
                "acciones": ["Reintentar la auditoria con el texto completo de la publicacion."],
            }
            decision = "Auditoria fallo: se informa el fallo sin retry adicional."
        elif _es_publicacion_vaga(texto, auditoria):
            resultado = redactar(
                modo="proponer_revision",
                texto=texto,
                categoria=categoria,
                auditoria=auditoria,
                experiencias=estado.get("experiencias_previas") or [],
            )
            decision = "Publicacion vaga: se propone una revision en vez de un informe de incumplimiento."
        else:
            resultado = redactar(
                modo="informe_auditoria",
                texto=texto,
                categoria=categoria,
                auditoria=auditoria,
                experiencias=estado.get("experiencias_previas") or [],
            )
            decision = "Informe de auditoria redactado."
        return {
            "redaccion": resultado,
            "pasos_ejecutados": [{"paso": "redaccion", "ok": True}],
            "bitacora": [{"nodo": "subagente_redactor", "decision": decision}],
        }
    except Exception as e:
        return _error_paso("redaccion", e)


def nodo_guardar_memoria(estado: dict) -> dict:
    """Subagente de memoria (escritura): persiste la experiencia auditada."""
    auditoria = estado.get("auditoria")
    if auditoria is None:
        return {
            "pasos_ejecutados": [{"paso": "guardar_memoria", "ok": True}],
            "bitacora": [
                {
                    "nodo": "subagente_guardar_memoria",
                    "decision": "Sin veredicto que persistir: paso omitido.",
                }
            ],
        }
    try:
        guardar_experiencia(
            texto=estado.get("publicacion", ""),
            categoria=estado.get("categoria", "general"),
            estado=auditoria.get("estado", "alerta"),
            resumen=f"{len(auditoria.get('alertas', []))} alertas",
        )
        return {
            "pasos_ejecutados": [{"paso": "guardar_memoria", "ok": True}],
            "bitacora": [
                {
                    "nodo": "subagente_guardar_memoria",
                    "decision": "Experiencia guardada en memoria de largo plazo.",
                }
            ],
        }
    except Exception as e:
        return _error_paso("guardar_memoria", e)


NODOS_PASO = {
    "memoria": nodo_memoria,
    "consulta_normativa": nodo_consulta_normativa,
    "auditoria": nodo_auditoria,
    "redaccion": nodo_redaccion,
    "guardar_memoria": nodo_guardar_memoria,
}


def _es_publicacion_vaga(texto: str, auditoria: dict) -> bool:
    """Detecta publicaciones insuficientes para proponer una revision.

    Senales combinadas (toma de decisiones adaptativa):
    - veredicto no_cumple sin alertas tecnicas, o con alerta de la plataforma
    - texto demasiado corto para describir el trabajo
    - el usuario pide "ayuda" sin detallar
    """
    alertas = auditoria.get("alertas", [])
    if auditoria.get("estado") == "no_cumple" and not alertas:
        return True
    if any(str(a.get("fuente", "")).startswith("Plataforma") for a in alertas):
        return True
    t = texto.strip().lower()
    return len(t) < 30 or "ayuda" in t


def _error_paso(paso: str, error: Exception) -> dict:
    logger.warning("Paso '%s' fallo: %s", paso, error)
    return {
        "errores": [{"paso": paso, "error": str(error)}],
        "pasos_ejecutados": [{"paso": paso, "ok": False}],
        "bitacora": [
            {
                "nodo": f"subagente_{paso}",
                "decision": f"FALLO: {type(error).__name__}: {error}",
            }
        ],
    }
