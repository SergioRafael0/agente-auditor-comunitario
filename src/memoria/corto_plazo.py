"""Memoria de corto plazo: persistencia del estado del grafo (checkpointer).

El checkpointer guarda el estado completo del grafo despues de cada paso,
agrupado por thread_id. Esto permite:
- Continuar una conversacion/elaboracion multi-turno sin perder contexto.
- Reanudar tareas interrumpidas (flujos prolongados).
"""

from __future__ import annotations

import os
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


def construir_checkpointer() -> BaseCheckpointSaver:
    """Devuelve un checkpointer Sqlite (persistente en disco) o Memory (en RAM).

    Si MEMORIA_CHECKPOINT define una ruta se usa SqliteSaver sobre ese archivo;
    en otro caso MemorySaver (suficiente para demo de una sesion).
    """
    ruta = os.getenv("MEMORIA_CHECKPOINT", "")
    if not ruta:
        return MemorySaver()
    from langgraph.checkpoint.sqlite import SqliteSaver

    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    import sqlite3

    conn = sqlite3.connect(ruta, check_same_thread=False)
    return SqliteSaver(conn)
