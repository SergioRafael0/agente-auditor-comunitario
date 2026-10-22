"""Tool de consulta: busqueda semantica de normativa en el indice RAG.

Reutiliza el retriever de la Evaluacion 1 (Chroma + sentence-transformers)
y lo expone como herramienta que el agente puede invocar de forma autonoma.
"""

from __future__ import annotations

from src.retriever.search import buscar


def buscar_normativa(texto: str, categoria: str | None = None, top_k: int = 5) -> dict:
    """Busca fragmentos de normativa relevante para una consulta.

    Devuelve dict con la lista de fragmentos (fuente, articulo, texto, score)
    y un resumen de la operacion para la bitacora del agente.
    """
    fragmentos = buscar(texto, categoria=categoria, top_k=top_k)
    return {
        "fragmentos": fragmentos,
        "n_fragmentos": len(fragmentos),
        "fuentes": sorted({f["fuente"] for f in fragmentos if f.get("fuente")}),
    }
