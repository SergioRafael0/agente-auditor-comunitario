"""Construccion del grafo LangGraph: supervisor + subagentes.

Topologia:

  START -> planificador -> enrutador --(condicional)--> subagentes -> enrutador
  enrutador --(plan completo)--> finalizador -> END

El enrutador es el supervisor: recorre el plan priorizado paso a paso,
invoca cada subagente segun condiciones del estado y cierra al terminar.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid

from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from src.grafo.enrutador import enrutador, siguiente_nodo
from src.grafo.estado import EstadoAgente
from src.grafo.planificador import planificar
from src.grafo.subagentes import NODOS_PASO
from src.observabilidad import trazas
from src.observabilidad.instrumentacion import nodo_instrumentado
from src.util.privacidad import texto_para_log

logger = logging.getLogger(__name__)

NODO_FINALIZADOR = "finalizador"


@nodo_instrumentado("planificador")
def nodo_planificador(estado: EstadoAgente) -> dict:
    """Supervisor: decide tipo de tarea y construye el plan priorizado."""
    inicio = time.time()
    tipo, plan = planificar(estado.get("publicacion", ""), estado.get("categoria", "general"))
    return {
        "tipo_tarea": tipo,
        "plan": plan,
        "pasos_ejecutados": [{"paso": f"planificar:{tipo}", "ok": True}],
        "bitacora": [
            {
                "nodo": "supervisor_planificador",
                "decision": f"Tipo de tarea '{tipo}'. Plan de {len(plan)} pasos priorizados"
                f" ({', '.join(p['nombre'] for p in plan)}). Generado en {int((time.time() - inicio) * 1000)} ms.",
            }
        ],
    }


@nodo_instrumentado("finalizador")
def nodo_finalizador(estado: EstadoAgente) -> dict:
    """Compone la respuesta final (sin LLM: resumen deterministico y trazable)."""
    partes = ["# Respuesta del Agente Auditor Comunitario\n"]
    auditoria = estado.get("auditoria")
    redaccion = estado.get("redaccion")

    if redaccion and redaccion.get("titulo"):
        partes.append(f"## {redaccion['titulo']}\n")
        cuerpos = [p for p in (redaccion.get("cuerpo"),) if p]
        for cuerpo in cuerpos:
            partes.append(cuerpo + "\n")
        acciones = redaccion.get("acciones") or []
        if acciones:
            partes.append("### Acciones recomendadas\n")
            partes.extend(f"- {a}" for a in acciones)

    if auditoria:
        alertas = auditoria.get("alertas", [])
        partes.append("## Veredicto normativo\n")
        partes.append(f"Estado: **{auditoria.get('estado', 'desconocido')}** ({len(alertas)} alertas)\n")
        for a in alertas:
            partes.append(
                f"- [{a.get('fuente', '')} {a.get('articulo', '')}] {a.get('mensaje', '')}"
                f" Recomendacion: {a.get('recomendacion', '')}"
            )

    if estado.get("errores"):
        partes.append("## Errores registrados\n")
        for e in estado["errores"]:
            partes.append(f"- Paso '{e.get('paso', '')}': {e.get('error', '')}")

    respuesta = "\n".join(partes).strip()
    return {
        "respuesta_final": respuesta,
        "pasos_ejecutados": [{"paso": "finalizador", "ok": True}],
        "bitacora": [{"nodo": "finalizador", "decision": "Respuesta final compuesta."}],
    }


def construir_grafo(checkpointer: BaseCheckpointSaver | None = None):
    """Construye el grafo compilado de LangGraph."""
    grafo = StateGraph(EstadoAgente)
    grafo.add_node("planificador", nodo_planificador)
    grafo.add_node("enrutador", enrutador)
    for nombre, funcion in NODOS_PASO.items():
        grafo.add_node(nombre, funcion)
    grafo.add_node(NODO_FINALIZADOR, nodo_finalizador)

    grafo.add_edge(START, "planificador")
    grafo.add_edge("planificador", "enrutador")
    for nombre in NODOS_PASO:
        grafo.add_edge(nombre, "enrutador")
    grafo.add_edge(NODO_FINALIZADOR, END)

    mapeo = {nombre: nombre for nombre in list(NODOS_PASO) + [NODO_FINALIZADOR]}
    grafo.add_conditional_edges("enrutador", siguiente_nodo, mapeo)

    return grafo.compile(checkpointer=checkpointer)


def invocar_agente(
    texto: str,
    categoria: str = "general",
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict:
    """Ejecuta el agente completo y devuelve el estado final.

    thread_id agrupa la conversacion para la memoria de corto plazo:
    en turnos sucesivos con el mismo id, el estado (historial de
    veredictos, errores y obtencion) se preserva via checkpointer.

    Cada ejecucion recibe un trace_id que correlaciona los eventos de
    data/eventos.jsonl con este registro en data/agente_ejecuciones.jsonl.
    """
    load_dotenv()
    if checkpointer is None:
        from src.memoria.corto_plazo import construir_checkpointer

        checkpointer = construir_checkpointer()

    grafo = construir_grafo(checkpointer)
    tid = thread_id or str(uuid.uuid4())
    traza = trazas.nueva_traza(tid)

    inicio = time.time()
    estado_final = grafo.invoke(
        {"publicacion": texto, "categoria": categoria, "trace_id": traza, "thread_id": tid},
        config={"configurable": {"thread_id": tid}},
    )
    logger.info("Agente completo en %d ms (thread %s)", int((time.time() - inicio) * 1000), tid)

    _loggear_ejecucion(tid, estado_final, latencia_ms=int((time.time() - inicio) * 1000))
    return estado_final


def _loggear_ejecucion(thread_id: str, estado: dict, latencia_ms: int) -> None:
    """Registro de la ejecucion completa del agente (observabilidad)."""
    import logging as _logging

    ruta = os.getenv("LOG_FILE_AGENTE", "data/agente_ejecuciones.jsonl")
    try:
        from pathlib import Path

        p = Path(ruta)
        p.parent.mkdir(parents=True, exist_ok=True)
        registro = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "trace_id": estado.get("trace_id"),
            "thread_id": thread_id,
            "input": {
                "texto": texto_para_log(estado.get("publicacion", "")),
                "categoria": estado.get("categoria", ""),
            },
            "tipo_tarea": estado.get("tipo_tarea", ""),
            "plan": [p_.get("nombre") for p_ in estado.get("plan", [])],
            "pasos_ejecutados": [e.get("paso") for e in estado.get("pasos_ejecutados", [])],
            "pasos_detalle": estado.get("pasos_ejecutados", []),
            "errores": estado.get("errores", []),
            "veredicto": (estado.get("auditoria") or {}).get("estado"),
            "latencia_total_ms": latencia_ms,
            "llm": trazas.resumen_llm(estado.get("trace_id")),
        }
        registro["bitacora"] = estado.get("bitacora", [])
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        _logging.getLogger(__name__).warning("No se pudo loggear la ejecucion: %s", e)


if __name__ == "__main__":
    import argparse

    load_dotenv()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Ejecutar el agente desde CLI.")
    parser.add_argument("--texto", required=True)
    parser.add_argument("--categoria", default="general")
    parser.add_argument("--thread-id", default=None)
    args = parser.parse_args()

    estado = invocar_agente(args.texto, args.categoria, args.thread_id)
    print(json.dumps({k: v for k, v in estado.items() if k not in ("bitacora", "pasos_ejecutados")}, indent=2, ensure_ascii=False))
    print("\n--- Bitacora de decisiones ---")
    for i, b in enumerate(estado.get("bitacora", []), 1):
        print(f"{i}. [{b['nodo']}] {b['decision']}")
