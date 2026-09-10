"""Convierte las salidas de scripts/eval_prompts.py al formato JSONL que espera src.agent.judge.

Luego corre el LLM-as-judge y guarda los resultados agregados.

Uso:
    python -m scripts.evaluar_con_judge
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.agent.judge import evaluar_registro

load_dotenv()

DIR_EVAL = Path("data/eval")
JSONL_TEMP = Path("data/judge_input.jsonl")
RESULTADO_PATH = Path("data/eval/judge_results.json")


def cargar_registros() -> list[dict]:
    """Convierte todos los JSON de data/eval/v* en registros JSONL."""
    registros: list[dict] = []
    for carpeta in sorted(DIR_EVAL.iterdir()):
        if not carpeta.is_dir() or carpeta.name.startswith("_"):
            continue
        for archivo in sorted(carpeta.glob("*.json")):
            if archivo.name.startswith("_") or archivo.name == "judge_results.json":
                continue
            data = json.loads(archivo.read_text(encoding="utf-8"))
            output = data.get("output", {})
            if not output or "error" in output:
                continue
            registro = {
                "interaccion_id": output.get("interaccion_id", archivo.stem),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tool": "revisar_publicacion",
                "input": {
                    "texto": data["caso"]["texto"],
                    "categoria": data["caso"]["categoria"],
                },
                "fragmentos_recuperados": output.get("fragmentos_recuperados", []),
                "respuesta": {
                    "estado": output.get("estado"),
                    "n_alertas": len(output.get("alertas", [])),
                    "alertas": output.get("alertas", []),
                },
                "latencia_ms": output.get("latencia_ms", 0),
                "_version_prompt": carpeta.name,
            }
            registros.append(registro)
    return registros


def guardar_jsonl(registros: list[dict]) -> None:
    JSONL_TEMP.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_TEMP.open("w", encoding="utf-8") as f:
        for reg in registros:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(f"  {len(registros)} registros guardados en {JSONL_TEMP}")


def evaluar_y_reportar(registros: list[dict]) -> None:
    print(f"\n  Evaluando {len(registros)} registros con LLM-as-judge...")
    resultados: list[dict] = []
    for i, reg in enumerate(registros, 1):
        print(f"    [{i}/{len(registros)}] {reg['_version_prompt']} :: {reg['interaccion_id'][:8]}", end=" ")
        scores = evaluar_registro(reg)
        print(f"-> relev={scores.get('relevancia_chunks')} fund={scores.get('fundamentacion')} comp={scores.get('completitud')}")
        resultados.append(
            {
                "interaccion_id": reg["interaccion_id"],
                "version_prompt": reg["_version_prompt"],
                "categoria": reg["input"]["categoria"],
                "estado_agente": reg["respuesta"]["estado"],
                "scores": scores,
            }
        )

    _guardar_resultados(resultados)
    _mostrar_resumen(resultados)


def _guardar_resultados(resultados: list[dict]) -> None:
    promedios = _calcular_promedios(resultados)
    payload = {
        "total_evaluaciones": len(resultados),
        "promedios_globales": promedios["globales"],
        "promedios_por_version": promedios["por_version"],
        "resultados_individuales": resultados,
    }
    RESULTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTADO_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Resultados guardados en {RESULTADO_PATH}")


def _calcular_promedios(resultados: list[dict]) -> dict:
    metricas = ["relevancia_chunks", "fundamentacion", "completitud"]

    def promedio_de(lista):
        out = {}
        for m in metricas:
            vals = [r["scores"].get(m) for r in lista if isinstance(r["scores"].get(m), (int, float))]
            out[m] = round(sum(vals) / len(vals), 3) if vals else None
        return out

    por_version: dict[str, dict] = {}
    for ver in {r["version_prompt"] for r in resultados}:
        subset = [r for r in resultados if r["version_prompt"] == ver]
        por_version[ver] = {
            "n": len(subset),
            "promedios": promedio_de(subset),
        }
    return {"globales": promedio_de(resultados), "por_version": por_version}


def _mostrar_resumen(resultados: list[dict]) -> None:
    promedios = _calcular_promedios(resultados)
    print("\n" + "=" * 60)
    print("RESUMEN LLM-AS-JUDGE")
    print("=" * 60)

    print("\nPromedios globales:")
    for k, v in promedios["globales"].items():
        print(f"  {k:25} {v}")

    print("\nPromedios por version de prompt:")
    for ver, data in promedios["por_version"].items():
        print(f"\n  {ver} (n={data['n']}):")
        for k, v in data["promedios"].items():
            print(f"    {k:25} {v}")


def main() -> None:
    print("Cargando registros de data/eval/...")
    registros = cargar_registros()
    if not registros:
        print("  No se encontraron registros. Corre primero scripts.eval_prompts --version v1 y v2.")
        return

    guardar_jsonl(registros)
    evaluar_y_reportar(registros)


if __name__ == "__main__":
    main()
