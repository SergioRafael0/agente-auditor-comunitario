"""Logica principal del agente auditor."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from src.agent.llm import generar
from src.agent.prompts import SYSTEM_AUDITOR, USER_TEMPLATE, few_shots_texto
from src.retriever.search import buscar

logger = logging.getLogger(__name__)


class Alerta(BaseModel):
    fuente: str
    articulo: str
    mensaje: str
    recomendacion: str


class ResultadoAuditoria(BaseModel):
    estado: str = Field(pattern=r"^(cumple|alerta|no_cumple)$")
    alertas: list[Alerta] = []
    recomendaciones_generales: list[str] = []


def auditar_publicacion(texto: str, categoria: str) -> dict:
    """Punto de entrada principal del agente.

    1. Recupera contexto normativo relevante.
    2. Llama al LLM con system prompt + contexto + publicacion.
    3. Parsea la respuesta JSON.
    4. Devuelve dict con el resultado + metadata de trazabilidad.
    """
    inicio = time.time()
    fragmentos = buscar(texto, categoria=categoria, top_k=5)

    contexto_partes = []
    for frag in fragmentos:
        cab = f"[{frag['fuente']}"
        if frag.get("articulo"):
            cab += f" - {frag['articulo']}"
        cab += "]"
        contexto_partes.append(f"{cab}\n{frag['texto']}")
    contexto = "\n\n---\n\n".join(contexto_partes) if contexto_partes else "(sin contexto recuperado)"

    user_msg = USER_TEMPLATE.format(texto=texto, categoria=categoria, contexto=contexto)
    system_msg = SYSTEM_AUDITOR + few_shots_texto()

    respuesta_llm = generar(system=system_msg, user=user_msg)

    try:
        data = json.loads(respuesta_llm)
        resultado = ResultadoAuditoria(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM no devolvio JSON valido: %s. Respuesta cruda: %s", e, respuesta_llm[:200])
        resultado = ResultadoAuditoria(
            estado="no_cumple",
            alertas=[
                Alerta(
                    fuente="Sistema",
                    articulo="-",
                    mensaje="El auditor no pudo generar una respuesta estructurada.",
                    recomendacion="Reintentar o consultar manualmente.",
                )
            ],
        )

    latencia_ms = int((time.time() - inicio) * 1000)
    interaccion_id = str(uuid.uuid4())

    resultado_dict = {
        "interaccion_id": interaccion_id,
        "estado": resultado.estado,
        "alertas": [a.model_dump() for a in resultado.alertas],
        "recomendaciones_generales": resultado.recomendaciones_generales,
        "fragmentos_recuperados": [
            {"fuente": f["fuente"], "articulo": f["articulo"], "score": f["score"]}
            for f in fragmentos
        ],
        "latencia_ms": latencia_ms,
    }

    _loggear_interaccion(
        {
            "interaccion_id": interaccion_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tool": "revisar_publicacion",
            "input": {"texto": texto, "categoria": categoria},
            "fragmentos_recuperados": resultado_dict["fragmentos_recuperados"],
            "respuesta": {
                "estado": resultado_dict["estado"],
                "n_alertas": len(resultado_dict["alertas"]),
            },
            "latencia_ms": latencia_ms,
        }
    )

    return resultado_dict


def _loggear_interaccion(registro: dict) -> None:
    ruta = Path(os.getenv("LOG_FILE", "data/interacciones.jsonl"))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import argparse

    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Probar el agente auditor desde CLI.")
    parser.add_argument("--texto", required=True, help="Descripcion de la publicacion")
    parser.add_argument("--categoria", default="general", help="Categoria (electricidad, ascensor, gas, agua, general)")
    args = parser.parse_args()

    resultado = auditar_publicacion(args.texto, args.categoria)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
