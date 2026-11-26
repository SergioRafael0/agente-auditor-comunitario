"""Tests del motor de metricas de observabilidad (IE1, IE2)."""

from __future__ import annotations

from src.observabilidad.metricas import (
    calcular_resumen,
    metricas_consistencia,
    metricas_errores,
    metricas_latencia,
    metricas_precision,
    metricas_recursos,
    percentil,
)


def test_percentil_interpola():
    valores = [10, 20, 30, 40, 50]
    assert percentil(valores, 50) == 30
    assert percentil(valores, 0) == 10
    assert percentil(valores, 100) == 50


def test_percentil_sin_valores():
    assert percentil([], 50) == 0.0
    assert percentil([7], 95) == 7.0


def test_metricas_precision_global_y_por_variabilidad():
    corridas = [
        {"escenario": "a", "variabilidad": "vaga", "estados_esperados": ["no_cumple"], "acierto": True},
        {"escenario": "b", "variabilidad": "vaga", "estados_esperados": ["no_cumple"], "acierto": False},
        {"escenario": "c", "variabilidad": "completa", "estados_esperados": ["alerta"], "acierto": True},
        {"escenario": "d", "variabilidad": "consulta", "estados_esperados": [], "acierto": True},
    ]
    m = metricas_precision(corridas)
    assert m["n"] == 3
    assert m["aciertos"] == 2
    assert m["precision"] == 0.667
    assert m["por_variabilidad"]["vaga"]["precision"] == 0.5
    assert m["por_variabilidad"]["completa"]["precision"] == 1.0


def test_metricas_consistencia_detecta_inestabilidad():
    corridas = [
        {"escenario": "a", "estados_esperados": ["alerta"], "estado_obtenido": "alerta"},
        {"escenario": "a", "estados_esperados": ["alerta"], "estado_obtenido": "alerta"},
        {"escenario": "b", "estados_esperados": ["alerta"], "estado_obtenido": "alerta"},
        {"escenario": "b", "estados_esperados": ["alerta"], "estado_obtenido": "cumple"},
    ]
    m = metricas_consistencia(corridas)
    assert m["n_escenarios"] == 2
    assert m["escenarios_estables"] == 1
    assert m["consistencia_global"] == 0.5
    assert m["por_escenario"]["a"]["estable"] is True
    assert m["por_escenario"]["b"]["estable"] is False
    assert m["por_escenario"]["b"]["veredicto_modal"] == "alerta"


def test_metricas_errores_agrega_fallbacks_y_nodos():
    eventos = [
        {"evento": "nodo", "nodo": "auditoria", "ok": True},
        {"evento": "nodo", "nodo": "redaccion", "ok": False},
        {"evento": "nodo", "nodo": "redaccion", "ok": False},
        {"evento": "fallback", "componente": "planificador"},
        {"evento": "llm_llamada", "degradada": True},
        {"evento": "llm_llamada", "degradada": False},
    ]
    ejecuciones = [{"errores": [{"paso": "redaccion"}]}, {"errores": []}]
    m = metricas_errores(eventos, ejecuciones)
    assert m["nodos_fallidos"] == 2
    assert m["fallos_por_nodo"] == {"redaccion": 2}
    assert m["fallbacks_por_componente"] == {"planificador": 1}
    assert m["llamadas_llm_degradadas"] == 1
    assert m["tasa_corridas_con_error"] == 0.5


def test_metricas_latencia_por_nodo_y_rol():
    eventos = [
        {"evento": "nodo", "nodo": "memoria", "latencia_ms": 100},
        {"evento": "nodo", "nodo": "memoria", "latencia_ms": 300},
        {"evento": "llm_llamada", "rol": "auditor", "latencia_ms": 1000},
    ]
    ejecuciones = [{"latencia_total_ms": 1500}, {"latencia_total_ms": 2500}]
    m = metricas_latencia(eventos, ejecuciones)
    assert m["latencia_total_ms"]["promedio"] == 2000.0
    assert m["latencia_total_ms"]["p95"] == 2450.0
    assert m["por_nodo"]["memoria"]["promedio_ms"] == 200.0
    assert m["por_rol_llm"]["auditor"]["llamadas"] == 1


def test_metricas_recursos_suma_tokens():
    eventos = [
        {"evento": "llm_llamada", "rol": "auditor", "tokens_entrada": 100, "tokens_salida": 50, "tokens_estimados": False},
        {"evento": "llm_llamada", "rol": "redaccion", "tokens_entrada": 200, "tokens_salida": 30, "tokens_estimados": True},
    ]
    m = metricas_recursos(eventos)
    assert m["tokens_entrada_total"] == 300
    assert m["tokens_salida_total"] == 80
    assert m["tokens_total"] == 380
    assert m["proporcion_tokens_estimados"] == 0.5
    assert m["por_rol"]["auditor"]["tokens_entrada"] == 100


def test_calcular_resumen_incluye_las_cinco_metricas():
    resumen = calcular_resumen([], [], [])
    assert set(resumen) == {"precision", "consistencia", "errores", "latencia", "recursos"}
