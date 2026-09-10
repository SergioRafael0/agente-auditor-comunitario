"""Bateria de pruebas para evaluar el prompt del agente.

Ejecuta el mismo conjunto de casos en una version dada del prompt
y guarda los resultados en data/eval/<version>/<caso>.json.

Uso:
    python -m scripts.eval_prompts --version v1
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.agent.auditor import auditar_publicacion

load_dotenv()

CASOS: list[dict] = [
    {
        "id": "ascensor_vago",
        "texto": "Necesito arreglar el ascensor del edificio que hace ruidos raros al subir. Es urgente.",
        "categoria": "ascensor",
        "esperado": ["alerta", "no_cumple"],
        "motivo": "Debe mencionar Registro de Mantenedores SEC/MINVU y autorizacion de asamblea",
    },
    {
        "id": "electricidad_tablero",
        "texto": "Necesito instalar un nuevo tablero electrico en el edificio",
        "categoria": "electricidad",
        "esperado": ["alerta"],
        "motivo": "Tableros electricos requieren instalador certificado SEC y RIC N°02",
    },
    {
        "id": "pintura_simple",
        "texto": "Necesito pintar el hall del edificio, color blanco, sin urgencia.",
        "categoria": "general",
        "esperado": ["alerta"],
        "motivo": "Obras en areas comunes requieren aprobacion de asamblea (Ley 21.442)",
    },
    {
        "id": "publicacion_vaga",
        "texto": "Necesito ayuda con unas cosas del edificio",
        "categoria": "general",
        "esperado": ["no_cumple"],
        "motivo": "Publicacion sin categoria ni detalle suficiente",
    },
    {
        "id": "jardinero_aprobado",
        "texto": "Busco jardinero para poda de arbustos en areas verdes comunes del condominio. El jardinero ya fue aprobado por la asamblea en sesion del mes pasado.",
        "categoria": "general",
        "esperado": ["cumple"],
        "motivo": "Ya aprobado por asamblea, sin alertas regulatorias",
    },
    {
        "id": "gas_caldera",
        "texto": "La caldera a gas del edificio no calienta bien. Necesito tecnico.",
        "categoria": "gas",
        "esperado": ["alerta"],
        "motivo": "Trabajos en gas requieren tecnico gasista certificado SEC",
    },
    {
        "id": "filtracion_bano",
        "texto": "Hay una filtracion en el bano del primer piso. Necesito un gasfiter.",
        "categoria": "agua",
        "esperado": ["cumple", "alerta"],
        "motivo": "Trabajo sanitario menor, deberia cumplir o dar alerta leve",
    },
    {
        "id": "cableado_estructural",
        "texto": "Necesito recablear todo el sistema electrico del edificio de 10 pisos porque tiene mas de 30 anos",
        "categoria": "electricidad",
        "esperado": ["alerta", "no_cumple"],
        "motivo": "Obra mayor electrica, requiere proyecto SEC, instalador certificado, RIC N°01 a N°06",
    },
]


def evaluar(version: str) -> None:
    carpeta = Path(f"data/eval/{version}")
    carpeta.mkdir(parents=True, exist_ok=True)

    resultados: list[dict] = []
    for i, caso in enumerate(CASOS, 1):
        print(f"\n[{i}/{len(CASOS)}] Caso: {caso['id']}")
        print(f"  Texto: {caso['texto'][:80]}...")
        print(f"  Esperado: {caso['esperado']} | Motivo: {caso['motivo'][:60]}...")

        inicio = time.time()
        try:
            output = auditar_publicacion(caso["texto"], caso["categoria"])
            latencia = int((time.time() - inicio) * 1000)
            estado_real = output.get("estado", "?")
            n_alertas = len(output.get("alertas", []))
            score = _calcular_score(caso, output)
            print(f"  -> estado={estado_real} | alertas={n_alertas} | score={score} | {latencia}ms")
        except Exception as e:
            output = {"error": str(e)}
            latencia = int((time.time() - inicio) * 1000)
            estado_real = "ERROR"
            n_alertas = 0
            score = 0
            print(f"  -> ERROR: {e}")

        resultado = {
            "caso": caso,
            "output": output,
            "latencia_ms": latencia,
            "estado_real": estado_real,
            "n_alertas": n_alertas,
            "score": score,
        }
        resultados.append(resultado)

        ruta = carpeta / f"{caso['id']}.json"
        ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    _resumir(resultados, version)


def _calcular_score(caso: dict, output: dict) -> int:
    """Score: 1 si el estado real esta en la lista de estados aceptables del caso."""
    return 1 if output.get("estado") in caso["esperado"] else 0


def _resumir(resultados: list[dict], version: str) -> None:
    total = len(resultados)
    aciertos = sum(r["score"] for r in resultados)
    errores = sum(1 for r in resultados if r["estado_real"] == "ERROR")
    latencia_promedio = sum(r["latencia_ms"] for r in resultados if r["estado_real"] != "ERROR") / max(1, total - errores)

    print(f"\n{'='*60}")
    print(f"RESUMEN {version}")
    print(f"{'='*60}")
    print(f"Casos totales:      {total}")
    print(f"Aciertos:           {aciertos}/{total} ({aciertos/total*100:.0f}%)")
    print(f"Errores:            {errores}")
    print(f"Latencia promedio:  {latencia_promedio:.0f}ms")
    print()

    for r in resultados:
        marca = "OK " if r["score"] else "FAIL"
        print(f"  {marca} {r['caso']['id']:25} esperado={r['caso']['esperado']:12} -> {r['estado_real']:12} ({r['n_alertas']} alertas)")

    resumen_path = Path(f"data/eval/{version}/_resumen.json")
    resumen_path.write_text(
        json.dumps(
            {
                "version": version,
                "total": total,
                "aciertos": aciertos,
                "porcentaje_aciertos": aciertos / total * 100,
                "errores": errores,
                "latencia_promedio_ms": latencia_promedio,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bateria de eval de prompts")
    parser.add_argument("--version", required=True, help="Etiqueta de la version (v1, v2, ...)")
    args = parser.parse_args()

    evaluar(args.version)
