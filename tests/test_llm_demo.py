"""Tests del modo demo del LLM (probar sin API key)."""

from __future__ import annotations

import json

from src.agent.llm import generar, modo_demo
from src.agent.respuestas_demo import simular


def test_simular_planificador_para_trabajo_concreto():
    raw = simular(
        "Eres el planificador de un agente de auditoria normativa.",
        "Categoria: electricidad\nPublicacion: Necesito arreglar el porton electrico del edificio",
    )
    data = json.loads(raw)
    assert data["tipo_tarea"] == "auditoria"
    assert [p["nombre"] for p in data["pasos"]] == [
        "memoria",
        "auditoria",
        "redaccion",
        "guardar_memoria",
    ]


def test_simular_planificador_para_consulta_normativa():
    raw = simular(
        "Eres el planificador de un agente de auditoria normativa.",
        "Categoria: ascensor\nPublicacion: Que exige la ley sobre mantencion de ascensores?",
    )
    data = json.loads(raw)
    assert data["tipo_tarea"] == "consulta_normativa"


def test_simular_auditor_para_publicacion_vaga():
    raw = simular(
        "Eres un auditor normativo experto en legislacion chilena.",
        "Publicacion a auditar:\nNecesito ayuda con unas cosas del edificio",
    )
    data = json.loads(raw)
    assert data["estado"] == "no_cumple"
    assert data["alertas"][0]["fuente"].startswith("Plataforma")


def test_simular_auditor_para_trabajo_concreto():
    raw = simular(
        "Eres un auditor normativo experto en legislacion chilena.",
        "Publicacion a auditar:\nNecesito instalar un tablero electrico en el edificio",
    )
    data = json.loads(raw)
    assert data["estado"] == "alerta"
    assert len(data["alertas"]) >= 1


def test_simular_redactor_para_publicacion_vaga_no_inventa():
    raw = simular(
        "Eres el redactor comunitario especializado.",
        "MODO: proponer_revision\n\nPublicacion vaga o insuficiente (categoria=general): ayuda",
    )
    data = json.loads(raw)
    assert "[COMPLETAR]" in data["cuerpo"]
    assert "empalme" not in data["cuerpo"].lower()


def test_generar_en_modo_demo_devuelve_json_sin_api(monkeypatch):
    monkeypatch.setenv("LLM_MODO", "offline")
    raw = generar(
        system="Eres un auditor normativo experto en legislacion chilena.",
        user="Publicacion a auditar:\nNecesito instalar un tablero electrico",
    )
    data = json.loads(raw)
    assert data["estado"] in ("alerta", "cumple", "no_cumple")


def test_modo_demo_se_activa_sin_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODO", raising=False)
    assert modo_demo() is True


def test_modo_demo_se_activa_con_llm_modo_offline(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-valida")
    monkeypatch.setenv("LLM_MODO", "offline")
    assert modo_demo() is True


def test_modo_demo_desactivado_con_api_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-valida")
    monkeypatch.delenv("LLM_MODO", raising=False)
    assert modo_demo() is False
