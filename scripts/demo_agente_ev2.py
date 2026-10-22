"""Demo de la Evaluacion 2: 5 escenarios de decisiones adaptativas.

Corre el agente completo (grafo LangGraph) en 5 escenarios disenados para
evidenciar los criterios IE1, IE3, IE4, IE5 e IE7 de la rubrica. Guarda un
JSON por escenario en data/eval/ev2/ y un resumen agregado al final.

Uso:
    python -m scripts.demo_agente_ev2            # corre los 5 escenarios
    python -m scripts.demo_agente_ev2 --num 2    # solo escenario 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

from src.grafo.grafo import invocar_agente

load_dotenv()
logger = logging.getLogger(__name__)

DIR_EVIDENCIA = Path("data/eval/ev2")


def _extraer_resumen(estado: dict) -> dict:
    return {
        "tipo_tarea": estado.get("tipo_tarea"),
        "plan": [p["nombre"] for p in estado.get("plan", [])],
        "veredicto": (estado.get("auditoria") or {}).get("estado"),
        "n_alertas": len((estado.get("auditoria") or {}).get("alertas", [])),
        "modo_redaccion": (estado.get("redaccion") or {}).get("modo"),
        "experiencias_previas": len(estado.get("experiencias_previas", [])),
        "errores": estado.get("errores", []),
    }


def _bitacora(estado: dict) -> list[str]:
    return [f"[{b['nodo']}] {b['decision']}" for b in estado.get("bitacora", [])]


def escenario_1_auditoria_normal() -> dict:
    estado = invocar_agente(
        "Necesito instalar un porton electrico nuevo en el acceso principal del edificio",
        categoria="electricidad",
        thread_id="demo-ev2-s1",
    )
    _criterio = "IE5: plan previamente priorizado (memoria -> auditoria -> redaccion -> guardar_memoria)."
    return {
        "nombre": "auditoria_normal",
        "criterio": _criterio,
        "resumen": _extraer_resumen(estado),
        "decisiones": _bitacora(estado),
    }


def escenario_2_auditoria_vaga() -> dict:
    estado = invocar_agente(
        "Necesito ayuda con unas cosas del edificio",
        categoria="general",
        thread_id="demo-ev2-s2",
    )
    _criterio = "IE7: decision adaptativa ante publicacion vaga -> el redactor propone revision en vez de informar incumplimiento."
    return {
        "nombre": "auditoria_vaga",
        "criterio": _criterio,
        "esperado": {"modo_redaccion": "proponer_revision"},
        "resumen": _extraer_resumen(estado),
        "decisiones": _bitacora(estado),
    }


def escenario_3_consulta_normativa() -> dict:
    estado = invocar_agente(
        "Que exige la normativa SEC para cambiar el tablero electrico de un edificio?",
        categoria="electricidad",
        thread_id="demo-ev2-s3",
    )
    _criterio = "IE7: decision adaptativa de ruta -> tarea de consulta con plan distinto (sin auditoria)."
    return {
        "nombre": "consulta_normativa",
        "criterio": _criterio,
        "esperado": {"tipo_tarea": "consulta_normativa"},
        "resumen": _extraer_resumen(estado),
        "decisiones": _bitacora(estado),
    }


def escenario_4_memoria_largo_plazo() -> dict:
    estado = invocar_agente(
        "Instalar puerta automatizada electricamente en el acceso del condominio",
        categoria="electricidad",
        thread_id="demo-ev2-s4",
    )
    _criterio = "IE3: memoria de largo plazo -> recupera experiencias auditadas previas por similitud."
    return {
        "nombre": "memoria_largo_plazo",
        "criterio": _criterio,
        "esperado": {"experiencias_previas": ">= 1"},
        "resumen": _extraer_resumen(estado),
        "decisiones": _bitacora(estado),
    }


def escenario_5_planificador_degradado() -> dict:
    """El LLM del planificador falla: el agente degrada a heuristica y sigue ejecutando."""
    from unittest.mock import patch

    import src.grafo.planificador as planificador

    with patch.object(planificador, "generar", return_value="esto no es json"):
        estado = invocar_agente(
            "Necesito reparar la caldera a gas de la sala de maquinas",
            categoria="gas",
            thread_id="demo-ev2-s5",
        )
    _criterio = "IE7: decision adaptativa ante LLM indisponible -> plan heuristico, flujo completo sin interrumpirse."
    return {
        "nombre": "planificador_degradado",
        "criterio": _criterio,
        "esperado": {"tipo_tarea": "auditoria", "plan": "heuristico"},
        "resumen": _extraer_resumen(estado),
        "decisiones": _bitacora(estado),
    }


ESCENARIOS = [
    escenario_1_auditoria_normal,
    escenario_2_auditoria_vaga,
    escenario_3_consulta_normativa,
    escenario_4_memoria_largo_plazo,
    escenario_5_planificador_degradado,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo de decisiones adaptativas (EV2).")
    parser.add_argument("--num", type=int, help="Correr solo el escenario N (1-5).")
    args = parser.parse_args()

    DIR_EVIDENCIA.mkdir(parents=True, exist_ok=True)
    seleccion = ESCENARIOS[args.num - 1 : args.num] if args.num else ESCENARIOS

    resultados = []
    for i, correr in enumerate(seleccion, start=(args.num or 1)):
        logger.info("Escenario %d: %s ...", i, correr.__name__)
        inicio = time.time()
        try:
            evidencia = correr()
            evidencia["ok"] = True
        except Exception as e:
            evidencia = {"nombre": correr.__name__, "ok": False, "error": f"{type(e).__name__}: {e}"}
        evidencia["segundos"] = round(time.time() - inicio, 1)
        resultados.append(evidencia)
        ruta = DIR_EVIDENCIA / f"evidencia_{evidencia['nombre']}.json"
        ruta.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[escenario {i}] {evidencia.get('ok') and 'OK' or 'FALLO'} -> {ruta}")

    resumen_ruta = DIR_EVIDENCIA / "resumen.json"
    resumen_ruta.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in resultados if r.get("ok"))
    print(f"\n{ok}/{len(resultados)} escenarios OK. Resumen: {resumen_ruta}")


if __name__ == "__main__":
    main()
