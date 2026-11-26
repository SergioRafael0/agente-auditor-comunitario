"""Tests de observabilidad: trazas, eventos, instrumentacion y privacidad."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.agent import llm
from src.observabilidad import trazas
from src.observabilidad.instrumentacion import nodo_instrumentado, registrar_llamada_llm
from src.util.privacidad import anonimizar_texto, hash_texto, texto_para_log


def _leer_jsonl(ruta) -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]


# --- trazas ---


def test_nueva_traza_asigna_ids():
    tid = trazas.nueva_traza("thread-1")
    assert tid
    assert trazas.trace_id() == tid
    assert trazas.thread_id() == "thread-1"


def test_asegurar_traza_reutiliza_la_activa():
    primera = trazas.asegurar_traza()
    segunda = trazas.asegurar_traza()
    assert primera == segunda


def test_registrar_evento_persiste_en_jsonl(tmp_path, monkeypatch):
    ruta = tmp_path / "eventos.jsonl"
    monkeypatch.setenv("LOG_FILE_EVENTOS", str(ruta))
    trazas.nueva_traza()
    trazas.registrar_evento("nodo", nodo="memoria", latencia_ms=5, ok=True)

    eventos = _leer_jsonl(ruta)
    assert len(eventos) == 1
    assert eventos[0]["evento"] == "nodo"
    assert eventos[0]["trace_id"] == trazas.trace_id()
    assert eventos[0]["timestamp"]


def test_eventos_traza_filtra_por_trace_id():
    trazas.reiniciar()
    traza_a = trazas.nueva_traza()
    trazas.registrar_evento("nodo", nodo="a")
    trazas.activar_traza("otra-traza")
    trazas.registrar_evento("nodo", nodo="b")

    assert [e["nodo"] for e in trazas.eventos_traza(traza_a)] == ["a"]


def test_resumen_llm_agrega_tokens_y_modos():
    trazas.nueva_traza()
    registrar_llamada_llm("auditor", "modelo-x", 0.2, _inicio(), modo="real",
                          tokens_entrada=100, tokens_salida=40)
    registrar_llamada_llm("redaccion", "modelo-x", 0.2, _inicio(), modo="demo",
                          texto_entrada="hola mundo", texto_salida="respuesta simulada")

    resumen = trazas.resumen_llm()
    assert resumen["llamadas_llm"] == 2
    assert resumen["tokens_entrada"] >= 100
    assert resumen["tokens_salida"] > 0
    assert resumen["modos"] == ["demo", "real"]


# --- instrumentacion ---


def _inicio() -> float:
    import time

    return time.time() - 0.01


def test_nodo_instrumentado_agrega_latencia_y_evento():
    trazas.nueva_traza()

    @nodo_instrumentado("prueba")
    def nodo(estado: dict) -> dict:
        return {"pasos_ejecutados": [{"paso": "prueba", "ok": True}]}

    resultado = nodo({"trace_id": trazas.trace_id()})
    assert "latencia_ms" in resultado["pasos_ejecutados"][0]
    eventos = trazas.eventos_traza()
    assert eventos[0]["evento"] == "nodo"
    assert eventos[0]["nodo"] == "prueba"
    assert eventos[0]["ok"] is True


def test_nodo_instrumentado_marca_fallo():
    trazas.nueva_traza()

    @nodo_instrumentado("prueba")
    def nodo(estado: dict) -> dict:
        return {"pasos_ejecutados": [{"paso": "prueba", "ok": False}]}

    nodo({})
    assert trazas.eventos_traza()[0]["ok"] is False


def test_llamada_llm_demo_estima_tokens():
    trazas.nueva_traza()
    evento = registrar_llamada_llm(
        "auditor", "modelo-x", 0.2, _inicio(), modo="demo",
        texto_entrada="una publicacion de prueba", texto_salida="respuesta",
    )
    assert evento["tokens_estimados"] is True
    assert evento["tokens_entrada"] > 0
    assert evento["modo"] == "demo"
    assert evento["ok"] is True


def test_llamada_llm_fallback_no_es_ok():
    evento = registrar_llamada_llm(
        "auditor", "modelo-x", 0.2, _inicio(), modo="fallback_demo",
        error="ValueError: sin conexion",
    )
    assert evento["ok"] is False
    assert evento["degradada"] is True
    assert "error" in evento


# --- instrumentacion de generar() ---


def test_generar_demo_registra_evento_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_demo_forzado", False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODO", raising=False)
    trazas.nueva_traza()

    llm.generar("system", "user", rol="auditor")

    eventos = trazas.eventos_traza()
    assert len(eventos) == 1
    assert eventos[0]["evento"] == "llm_llamada"
    assert eventos[0]["rol"] == "auditor"
    assert eventos[0]["modo"] == "demo"


def test_generar_degrada_a_demo_y_registra_fallo(monkeypatch):
    monkeypatch.setattr(llm, "_demo_forzado", False)
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("LLM_MODO", raising=False)
    trazas.nueva_traza()

    with patch.object(llm, "cliente", side_effect=ValueError("sin conexion")):
        texto = llm.generar("system", "user")

    assert texto
    eventos = trazas.eventos_traza()
    assert eventos[0]["modo"] == "fallback_demo"
    assert eventos[0]["degradada"] is True
    assert "ValueError" in eventos[0]["error"]


# --- privacidad ---


def test_anonimizar_texto_enmascara_datos_personales():
    texto = "Contactar a juan.perez@correo.cl o al 9 8765 4321, RUT 12.345.678-9"
    anonimo = anonimizar_texto(texto)
    assert "juan.perez@correo.cl" not in anonimo
    assert "12.345.678-9" not in anonimo
    assert "[CORREO]" in anonimo
    assert "[RUT]" in anonimo
    assert "[TELEFONO]" in anonimo


def test_hash_texto_estable_y_corto():
    assert hash_texto("hola") == hash_texto("hola")
    assert hash_texto("hola") != hash_texto("adios")
    assert len(hash_texto("hola")) == 16


def test_texto_para_log_respeta_variable_de_entorno(monkeypatch):
    texto = "llamar al 9 8765 4321"
    monkeypatch.setenv("LOG_ANONIMIZAR", "1")
    assert "8765" not in texto_para_log(texto)
    monkeypatch.setenv("LOG_ANONIMIZAR", "0")
    assert texto_para_log(texto) == texto


# --- correlacion de traza end-to-end ---


def test_invocar_agente_correlaciona_traza_en_log(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_FILE_AGENTE", str(tmp_path / "agente.jsonl"))
    from unittest.mock import patch as _patch

    from src.grafo import planificador as _planificador
    from src.grafo.grafo import invocar_agente

    plan_llm = json.dumps(
        {
            "tipo_tarea": "auditoria",
            "pasos": [{"nombre": "memoria", "prioridad": 1, "justificacion": "primero"}],
        }
    )
    with (
        _patch.object(_planificador, "generar", return_value=plan_llm),
        _patch("src.grafo.subagentes.buscar_experiencias", return_value=[]),
    ):
        estado = invocar_agente("instalar un tablero electrico", "electricidad", thread_id="t-corr")

    registros = _leer_jsonl(tmp_path / "agente.jsonl")
    registro = registros[-1]
    assert registro["trace_id"] == estado["trace_id"]
    assert registro["trace_id"]
    assert registro["thread_id"] == "t-corr"
    assert "llm" in registro
    assert all("latencia_ms" in paso for paso in registro["pasos_detalle"])
