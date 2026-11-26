"""Tests del analisis de logs y trazas (IE3)."""

from __future__ import annotations

import json

from src.observabilidad.analisis import (
    analizar,
    anomalias,
    cargar_jsonl,
    cuellos_de_botella,
    hallazgos,
    patrones,
    puntos_de_falla,
)


def test_cargar_jsonl_tolerante_a_archivo_inexistente(tmp_path):
    assert cargar_jsonl(tmp_path / "no_existe.jsonl") == []


def test_cargar_jsonl_tolerante_a_lineas_invalidas(tmp_path):
    ruta = tmp_path / "datos.jsonl"
    ruta.write_text('{"a": 1}\n\nesto no es json\n{"b": 2}\n', encoding="utf-8")
    assert cargar_jsonl(ruta) == [{"a": 1}, {"b": 2}]


def test_cuellos_de_botella_ordena_por_latencia():
    eventos = [
        {"evento": "nodo", "nodo": "auditoria", "latencia_ms": 900},
        {"evento": "nodo", "nodo": "memoria", "latencia_ms": 100},
        {"evento": "llm_llamada", "rol": "auditor", "latencia_ms": 800},
    ]
    c = cuellos_de_botella(eventos)
    assert c["por_nodo"][0]["nombre"] == "auditoria"
    assert c["cuello_de_botella_principal"] == "auditoria"
    assert c["llm_vs_resto"]["proporcion_llm"] == 0.8


def test_puntos_de_falla_detecta_reintentos_y_fallbacks():
    eventos = [
        {"evento": "nodo", "nodo": "redaccion", "ok": False},
        {"evento": "fallback", "componente": "planificador", "detalle": "JSON"},
        {"evento": "llm_llamada", "rol": "auditor", "degradada": True, "error": "timeout"},
    ]
    ejecuciones = [
        {
            "trace_id": "t1",
            "pasos_detalle": [{"paso": "auditoria"}, {"paso": "auditoria"}],
            "errores": [{"paso": "redaccion", "error": "fallo"}],
        }
    ]
    f = puntos_de_falla(eventos, ejecuciones)
    assert f["fallos_por_nodo"] == {"redaccion": 1}
    assert f["reintentos"][0]["pasos_reintentados"] == ["auditoria"]
    assert f["fallbacks"][0]["componente"] == "planificador"
    assert f["llamadas_degradadas"][0]["rol"] == "auditor"
    assert f["corridas_con_error"][0]["trace_id"] == "t1"


def test_anomalias_detecta_outliers_y_scores_bajos():
    ejecuciones = [
        {"trace_id": f"t{i}", "latencia_total_ms": lat}
        for i, lat in enumerate([100, 110, 90, 105, 95, 100, 105, 5000])
    ]
    interacciones = [
        {
            "interaccion_id": "i1",
            "fragmentos_recuperados": [{"fuente": "ley", "score": 0.2}],
        }
    ]
    a = anomalias([], ejecuciones, interacciones)
    assert a["outliers_latencia"][0]["latencia_total_ms"] == 5000
    assert a["n_fragmentos_score_bajo"] == 1
    assert a["fragmentos_score_bajo"][0]["score"] == 0.2


def test_patrones_agrega_por_categoria_y_tarea():
    ejecuciones = [
        {
            "input": {"categoria": "gas"},
            "errores": [{"paso": "x"}],
            "latencia_total_ms": 1000,
            "tipo_tarea": "auditoria",
            "veredicto": "alerta",
        },
        {
            "input": {"categoria": "gas"},
            "errores": [],
            "latencia_total_ms": 2000,
            "tipo_tarea": "auditoria",
            "veredicto": "no_cumple",
        },
    ]
    p = patrones(ejecuciones, [])
    assert p["por_categoria"]["gas"]["corridas"] == 2
    assert p["por_categoria"]["gas"]["con_error"] == 1
    assert p["por_categoria"]["gas"]["latencia_promedio_ms"] == 1500.0
    assert p["veredictos_por_tipo_tarea"]["auditoria"] == {"alerta": 1, "no_cumple": 1}


def test_hallazgos_incluye_cuello_y_fallas():
    eventos = [{"evento": "nodo", "nodo": "auditoria", "latencia_ms": 900, "ok": True}]
    cuellos = cuellos_de_botella(eventos)
    fallas = puntos_de_falla([], [])
    anom = anomalias([], [], [])
    patr = patrones([], [])
    hs = hallazgos(cuellos, fallas, anom, patr, eventos)
    assert any(h["tipo"] == "cuello_de_botella" for h in hs)
    assert "auditoria" in hs[0]["titulo"]


def test_analizar_estructura_completa(tmp_path):
    ruta_ev = tmp_path / "eventos.jsonl"
    ruta_ev.write_text(json.dumps({"evento": "nodo", "nodo": "memoria", "latencia_ms": 5, "ok": True}) + "\n", encoding="utf-8")
    reporte = analizar(str(ruta_ev), str(tmp_path / "nada.jsonl"), str(tmp_path / "nada2.jsonl"))
    assert set(reporte) == {
        "fuentes",
        "cuellos_de_botella",
        "puntos_de_falla",
        "anomalias",
        "patrones",
        "hallazgos",
    }
    assert reporte["fuentes"]["eventos"]["n"] == 1
