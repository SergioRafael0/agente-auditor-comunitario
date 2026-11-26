"""Analisis de logs del agente: cuellos de botella, fallas, anomalias y patrones (IE3).

Lee los tres registros del sistema, detecta los puntos criticos y genera:
- data/eval/ev3/analisis_logs.json : resultado completo (evidencia numerica)
- docs/analisis-logs-ev3.md        : informe de hallazgos legible

Uso:
    python -m scripts.analizar_logs
    python -m scripts.analizar_logs --eventos ruta --ejecuciones ruta --interacciones ruta
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from src.observabilidad.analisis import analizar

SALIDA_JSON = Path("data/eval/ev3/analisis_logs.json")
SALIDA_MD = Path("docs/analisis-logs-ev3.md")


def _tabla(filas: list[list[str]], cabeceras: list[str]) -> str:
    linea_cab = "| " + " | ".join(cabeceras) + " |"
    linea_sep = "| " + " | ".join("---" for _ in cabeceras) + " |"
    cuerpo = ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join([linea_cab, linea_sep, *cuerpo])


def generar_markdown(reporte: dict) -> str:
    """Convierte el reporte de analisis en un informe markdown."""
    partes = [
        "# Analisis de logs y trazas del agente (IE3)",
        "",
        f"Generado: {reporte.get('generado', '')} por `scripts/analizar_logs.py`.",
        "",
        "## Fuentes analizadas",
        "",
    ]
    filas = [
        [f["ruta"], f["n"]] for f in reporte["fuentes"].values()
    ]
    partes.append(_tabla(filas, ["Registro", "Lineas"]))
    partes.append("")

    partes.append("## Hallazgos priorizados")
    partes.append("")
    for i, h in enumerate(reporte["hallazgos"], 1):
        partes.append(f"{i}. **[{h['tipo']}]** {h['titulo']}")
    partes.append("")

    partes.append("## Cuellos de botella")
    partes.append("")
    partes.append("### Por nodo del grafo")
    partes.append("")
    filas = [
        [n["nombre"], n["n"], n["total_ms"], n["promedio_ms"], n["p95_ms"], f"{round(n['proporcion'] * 100)}%"]
        for n in reporte["cuellos_de_botella"]["por_nodo"]
    ]
    partes.append(_tabla(filas, ["Nodo", "Ejec.", "Total ms", "Promedio ms", "p95 ms", "% latencia"]))
    partes.append("")
    partes.append("### Por rol de llamada al LLM")
    partes.append("")
    filas = [
        [n["nombre"], n["n"], n["total_ms"], n["promedio_ms"], n["p95_ms"], f"{round(n['proporcion'] * 100)}%"]
        for n in reporte["cuellos_de_botella"]["por_rol_llm"]
    ]
    partes.append(_tabla(filas, ["Rol", "Llamadas", "Total ms", "Promedio ms", "p95 ms", "% latencia"]))
    partes.append("")
    prop = round(reporte["cuellos_de_botella"]["llm_vs_resto"]["proporcion_llm"] * 100)
    partes.append(f"Las llamadas al LLM concentran el **{prop}%** de la latencia total medida en nodos.")
    partes.append("")

    partes.append("## Puntos de falla")
    partes.append("")
    fallas = reporte["puntos_de_falla"]
    partes.append(f"- Fallos por nodo: `{fallas['fallos_por_nodo'] or 'ninguno'}`")
    partes.append(f"- Corridas con reintentos de pasos: **{len(fallas['reintentos'])}**")
    partes.append(f"- Fallbacks (degradaciones) registrados: **{len(fallas['fallbacks'])}**")
    partes.append(f"- Llamadas al LLM degradadas a modo demo: **{len(fallas['llamadas_degradadas'])}**")
    partes.append(f"- Corridas con errores en el estado: **{len(fallas['corridas_con_error'])}**")
    partes.append("")
    if fallas["corridas_con_error"]:
        filas = [
            [c["trace_id"], ", ".join(f"{e['paso']}: {e['error']}" for e in c["errores"])]
            for c in fallas["corridas_con_error"][:10]
        ]
        partes.append(_tabla(filas, ["trace_id", "Errores"]))
        partes.append("")

    partes.append("## Anomalias")
    partes.append("")
    anom = reporte["anomalias"]
    partes.append(f"- Corridas con latencia outlier: **{len(anom['outliers_latencia'])}**")
    partes.append(
        f"- Fragmentos recuperados con score < 0.35: **{anom['n_fragmentos_score_bajo']}**"
    )
    partes.append(f"- Nodos con latencia inestable: **{len(anom['nodos_latencia_inestable'])}**")
    partes.append("")
    if anom["outliers_latencia"]:
        filas = [
            [o["trace_id"], o["latencia_total_ms"], o["umbral_ms"]]
            for o in anom["outliers_latencia"][:10]
        ]
        partes.append(_tabla(filas, ["trace_id", "Latencia ms", "Umbral ms"]))
        partes.append("")

    partes.append("## Patrones")
    partes.append("")
    patrones = reporte["patrones"]
    filas = [
        [cat, f["corridas"], f["con_error"], f["latencia_promedio_ms"]]
        for cat, f in patrones["por_categoria"].items()
    ]
    partes.append(_tabla(filas, ["Categoria", "Corridas", "Con error", "Latencia promedio ms"]))
    partes.append("")
    partes.append("Distribucion de estados en interacciones:")
    partes.append("")
    partes.append(f"`{patrones['distribucion_estados_interacciones']}`")
    partes.append("")
    partes.append("Veredictos por tipo de tarea:")
    partes.append("")
    partes.append(f"`{patrones['veredictos_por_tipo_tarea']}`")
    partes.append("")
    return "\n".join(partes)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Analisis de logs y trazas del agente.")
    parser.add_argument("--eventos", default="data/eventos.jsonl")
    parser.add_argument("--ejecuciones", default="data/agente_ejecuciones.jsonl")
    parser.add_argument("--interacciones", default="data/interacciones.jsonl")
    parser.add_argument("--salida-json", default=str(SALIDA_JSON))
    parser.add_argument("--salida-md", default=str(SALIDA_MD))
    args = parser.parse_args()

    reporte = analizar(args.eventos, args.ejecuciones, args.interacciones)
    reporte["generado"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    salida_json = Path(args.salida_json)
    salida_json.parent.mkdir(parents=True, exist_ok=True)
    salida_json.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    salida_md = Path(args.salida_md)
    salida_md.parent.mkdir(parents=True, exist_ok=True)
    salida_md.write_text(generar_markdown(reporte), encoding="utf-8")

    print(f"Hallazgos: {len(reporte['hallazgos'])}")
    for h in reporte["hallazgos"]:
        print(f"  [{h['tipo']}] {h['titulo']}")
    print(f"\nEvidencia: {salida_json}")
    print(f"Informe: {salida_md}")


if __name__ == "__main__":
    main()
