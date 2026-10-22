"""Tests del grafo LangGraph: planificador, enrutador y flujo completo."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.grafo import enrutador, planificador
from src.grafo.grafo import construir_grafo
from src.grafo.estado import EstadoAgente, MAX_ITERACIONES


def _plan_json_llm():
    return json.dumps(
        {
            "tipo_tarea": "auditoria",
            "pasos": [
                {"nombre": "memoria", "prioridad": 1, "justificacion": "primero"},
                {"nombre": "auditoria", "prioridad": 2, "justificacion": "segundo"},
                {"nombre": "redaccion", "prioridad": 3, "justificacion": "tercero"},
                {"nombre": "guardar_memoria", "prioridad": 4, "justificacion": "cuarto"},
            ],
        }
    )


def test_planificador_llm_valido():
    with patch.object(planificador, "generar", return_value=_plan_json_llm()):
        tipo, plan = planificador.planificar("instalar tablero electrico", "electricidad")
    assert tipo == "auditoria"
    assert [p["nombre"] for p in plan] == ["memoria", "auditoria", "redaccion", "guardar_memoria"]


def test_planificador_fallback_heuristico():
    with patch.object(planificador, "generar", return_value="'{no json'"):
        tipo, plan = planificador.planificar("Necesito arreglar el porton electrico urgente", "electricidad")
    assert tipo == "auditoria"
    assert plan[0]["nombre"] == "memoria"
    assert [p["prioridad"] for p in plan] == sorted(p["prioridad"] for p in plan)


def test_planificador_heuristica_consulta_normativa():
    with patch.object(planificador, "generar", return_value="'{no json'"):
        tipo, plan = planificador.planificar("Que exige la ley para instalar un ascensor?", "ascensor")
    assert tipo == "consulta_normativa"
    assert "consulta_normativa" in [p["nombre"] for p in plan]
    assert "auditoria" not in [p["nombre"] for p in plan]


def test_enrutador_sigue_el_plan():
    estado = {
        "plan": [
            {"nombre": "memoria", "prioridad": 1, "justificacion": ""},
            {"nombre": "auditoria", "prioridad": 2, "justificacion": ""},
        ],
        "iteraciones": 0,
    }
    salida = enrutador.enrutador(estado)
    assert salida["nodo_siguiente"] == "memoria"
    assert salida["iteraciones"] == 1


def test_enrutador_reintenta_paso_fallado():
    estado = {
        "plan": [
            {"nombre": "auditoria", "prioridad": 1, "justificacion": ""},
            {"nombre": "redaccion", "prioridad": 2, "justificacion": ""},
        ],
        "pasos_ejecutados": [{"paso": "auditoria", "ok": False}],
        "iteraciones": 1,
    }
    salida = enrutador.enrutador(estado)
    assert salida["nodo_siguiente"] == "auditoria"
    assert "REINTENTO" in salida["bitacora"][0]["decision"]


def test_enrutador_salta_tras_dos_fallos():
    estado = {
        "plan": [
            {"nombre": "auditoria", "prioridad": 1, "justificacion": ""},
            {"nombre": "redaccion", "prioridad": 2, "justificacion": ""},
        ],
        "pasos_ejecutados": [
            {"paso": "auditoria", "ok": False},
            {"paso": "auditoria", "ok": False},
        ],
        "iteraciones": 2,
    }
    salida = enrutador.enrutador(estado)
    assert salida["nodo_siguiente"] == "redaccion"


def test_enrutador_omite_guardar_memoria_sin_veredicto():
    estado = {
        "plan": [
            {"nombre": "guardar_memoria", "prioridad": 1, "justificacion": ""},
            {"nombre": "redaccion", "prioridad": 2, "justificacion": ""},
        ],
        "pasos_ejecutados": [],
        "iteraciones": 0,
    }
    salida = enrutador.enrutador(estado)
    assert salida["nodo_siguiente"] == "redaccion"


def test_enrutador_corta_por_presupuesto():
    estado = {
        "plan": [{"nombre": "auditoria", "prioridad": 1, "justificacion": ""}],
        "pasos_ejecutados": [],
        "iteraciones": MAX_ITERACIONES,
    }
    salida = enrutador.enrutador(estado)
    assert salida["nodo_siguiente"] == "finalizador"


def test_grafo_completo_con_herramientas_mockeadas(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_FILE_AGENTE", str(tmp_path / "agente.jsonl"))

    estado_inicial = EstadoAgente(
        publicacion="instalar un tablero electrico nuevo en el edificio",
        categoria="electricidad",
    )

    auditoria_falsa = {
        "estado": "alerta",
        "alertas": [
            {
                "fuente": "RIC N°02",
                "articulo": "Punto 6.1",
                "mensaje": "Requiere instalador certificado SEC",
                "recomendacion": "Contratar instalador certificado",
            }
        ],
        "recomendaciones_generales": ["Pedir 2 cotizaciones"],
    }
    redaccion_falsa = {
        "modo": "informe_auditoria",
        "titulo": "Informe de auditoria",
        "cuerpo": "La publicacion requiere instalador certificado SEC.",
        "acciones": ["Contratar instalador certificado SEC"],
    }
    with (
        patch.object(planificador, "generar", return_value=_plan_json_llm()),
        patch("src.grafo.subagentes.auditar", return_value=auditoria_falsa),
        patch("src.grafo.subagentes.redactar", return_value=redaccion_falsa),
        patch("src.grafo.subagentes.buscar_experiencias", return_value=[]),
        patch("src.grafo.subagentes.guardar_experiencia", return_value="id-falso"),
    ):
        grafo = construir_grafo()
        estado = grafo.invoke(estado_inicial, config={"configurable": {"thread_id": "test"}})

    assert estado["tipo_tarea"] == "auditoria"
    assert estado["auditoria"]["estado"] == "alerta"
    assert estado["redaccion"]["titulo"] == "Informe de auditoria"
    assert "Veredicto normativo" in estado["respuesta_final"]
    pasos = [e["paso"] for e in estado["pasos_ejecutados"]]
    assert pasos.count("auditoria") == 1
    assert "guardar_memoria" in pasos
