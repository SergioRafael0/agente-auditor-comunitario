"""Tool de razonamiento: auditoria normativa de una publicacion.

Reutiliza sin cambios el nucleo de la Evaluacion 1 (RAG + LLM con prompt v2
y few-shots). El agente la invoca como herramienta cuando decide auditar.
"""

from __future__ import annotations

from src.agent.auditor import auditar_publicacion as _auditar_ev1


def auditar(texto: str, categoria: str = "general") -> dict:
    """Audita una publicacion contra la normativa y devuelve el veredicto.

    El dict resultante incluye estado, alertas con citas legales,
    recomendaciones, fragmentos recuperados y latencia.
    """
    resultado = _auditar_ev1(texto, categoria)
    resultado["categoria"] = categoria
    return resultado
