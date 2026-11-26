"""Fixtures compartidas de la bateria de tests."""

from __future__ import annotations

import pytest

from src.observabilidad import trazas

VARIABLES_LOG = (
    "LOG_FILE",
    "LOG_FILE_AGENTE",
    "LOG_FILE_EVENTOS",
    "LOG_FILE_ACCESOS",
)


@pytest.fixture(autouse=True)
def _aislar_logs(tmp_path, monkeypatch):
    """Cada test escribe sus logs en tmp_path y parte con buffer de trazas limpio."""
    for i, nombre in enumerate(VARIABLES_LOG):
        monkeypatch.setenv(nombre, str(tmp_path / f"log_{i}.jsonl"))
    monkeypatch.setenv("MEMORIA_CHECKPOINT", "")
    trazas.reiniciar()
    yield
    trazas.reiniciar()
