"""Analisis de logs y trazas del agente (Evaluacion 3, IE3).

Sobre los tres registros del sistema:
- data/interacciones.jsonl   : una linea por auditoria (tool revisar_publicacion)
- data/agente_ejecuciones.jsonl : una linea por corrida completa del grafo
- data/eventos.jsonl         : eventos granulares (llamadas LLM, nodos, fallbacks)

detecta cuellos de botella, puntos de falla, anomalias y patrones de
comportamiento. El CLI `scripts/analizar_logs.py` vuelca el resultado a
JSON y a un informe markdown; el dashboard (`src/observabilidad/dashboard.py`)
presenta los mismos calculos.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from src.observabilidad.metricas import percentil

UMBRAL_SCORE_BAJO = 0.35
FACTOR_OUTLIER = 2.0


def cargar_jsonl(ruta: str | Path) -> list[dict]:
    """Carga un JSONL tolerando lineas vacias y archivos inexistentes."""
    p = Path(ruta)
    if not p.exists():
        return []
    registros = []
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea:
            try:
                registros.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    return registros


def cuellos_de_botella(eventos: list[dict]) -> dict:
    """Identifica donde se concentra la latencia: nodos del grafo y llamadas LLM."""
    lat_nodos: dict[str, list[float]] = defaultdict(list)
    lat_llm: dict[str, list[float]] = defaultdict(list)
    for e in eventos:
        if e.get("evento") == "nodo":
            lat_nodos[e.get("nodo", "?")].append(e.get("latencia_ms", 0))
        elif e.get("evento") == "llm_llamada":
            lat_llm[e.get("rol", "?")].append(e.get("latencia_ms", 0))

    total_nodos = sum(sum(v) for v in lat_nodos.values())
    total_llm = sum(sum(v) for v in lat_llm.values())

    def _ranking(fuente: dict[str, list[float]], total: float) -> list[dict]:
        filas = []
        for nombre, vals in sorted(fuente.items(), key=lambda kv: -sum(kv[1])):
            suma = sum(vals)
            filas.append(
                {
                    "nombre": nombre,
                    "n": len(vals),
                    "total_ms": suma,
                    "promedio_ms": round(suma / len(vals), 1),
                    "p95_ms": percentil(vals, 95),
                    "proporcion": round(suma / total, 3) if total else 0.0,
                }
            )
        return filas

    ranking_nodos = _ranking(lat_nodos, total_nodos)
    ranking_llm = _ranking(lat_llm, total_llm)
    return {
        "por_nodo": ranking_nodos,
        "por_rol_llm": ranking_llm,
        "cuello_de_botella_principal": (ranking_nodos[0]["nombre"] if ranking_nodos else None),
        "llm_vs_resto": {
            "latencia_llm_ms": total_llm,
            "latencia_nodos_ms": total_nodos,
            "proporcion_llm": round(total_llm / total_nodos, 3) if total_nodos else 0.0,
        },
    }


def puntos_de_falla(eventos: list[dict], ejecuciones: list[dict]) -> dict:
    """Nodos fallidos, reintentos, fallbacks y corridas con errores."""
    fallos_nodo = Counter(
        e.get("nodo", "?") for e in eventos if e.get("evento") == "nodo" and not e.get("ok")
    )
    fallbacks = [
        {"componente": e.get("componente", "?"), "detalle": e.get("detalle", ""), "trace_id": e.get("trace_id")}
        for e in eventos
        if e.get("evento") == "fallback"
    ]
    degradadas = [
        {"rol": e.get("rol", "?"), "error": e.get("error", ""), "trace_id": e.get("trace_id")}
        for e in eventos
        if e.get("evento") == "llm_llamada" and e.get("degradada")
    ]
    reintentos = []
    corridas_con_error = []
    for ej in ejecuciones:
        pasos = [p.get("paso") for p in ej.get("pasos_detalle", [])]
        repetidos = [p for p, n in Counter(pasos).items() if n > 1]
        if repetidos:
            reintentos.append({"trace_id": ej.get("trace_id"), "pasos_reintentados": repetidos})
        if ej.get("errores"):
            corridas_con_error.append(
                {
                    "trace_id": ej.get("trace_id"),
                    "errores": [
                        {"paso": e.get("paso"), "error": e.get("error", "")[:200]} for e in ej["errores"]
                    ],
                }
            )
    return {
        "fallos_por_nodo": dict(fallos_nodo),
        "fallbacks": fallbacks,
        "llamadas_degradadas": degradadas,
        "reintentos": reintentos,
        "corridas_con_error": corridas_con_error,
    }


def anomalias(eventos: list[dict], ejecuciones: list[dict], interacciones: list[dict]) -> dict:
    """Outliers de latencia, retrieval con baja confianza y veredictos inconsistentes."""
    latencias = [ej.get("latencia_total_ms", 0) for ej in ejecuciones if ej.get("latencia_total_ms")]
    outliers = []
    if len(latencias) >= 3:
        promedio = sum(latencias) / len(latencias)
        varianza = sum((x - promedio) ** 2 for x in latencias) / len(latencias)
        desviacion = varianza ** 0.5
        umbral = promedio + FACTOR_OUTLIER * desviacion
        for ej in ejecuciones:
            lat = ej.get("latencia_total_ms", 0)
            if lat > umbral:
                outliers.append(
                    {"trace_id": ej.get("trace_id"), "latencia_total_ms": lat, "umbral_ms": round(umbral, 1)}
                )

    scores_bajos = []
    for it in interacciones:
        for frag in it.get("fragmentos_recuperados", []):
            if frag.get("score", 1.0) < UMBRAL_SCORE_BAJO:
                scores_bajos.append(
                    {
                        "interaccion_id": it.get("interaccion_id"),
                        "fuente": frag.get("fuente", ""),
                        "score": frag.get("score"),
                    }
                )

    lat_nodos: dict[str, list[float]] = defaultdict(list)
    for e in eventos:
        if e.get("evento") == "nodo":
            lat_nodos[e.get("nodo", "?")].append(e.get("latencia_ms", 0))
    nodos_inestables = []
    for nombre, vals in lat_nodos.items():
        if len(vals) >= 3:
            promedio = sum(vals) / len(vals)
            desviacion = (sum((x - promedio) ** 2 for x in vals) / len(vals)) ** 0.5
            if promedio > 0 and desviacion / promedio > 0.75:
                nodos_inestables.append(
                    {
                        "nodo": nombre,
                        "promedio_ms": round(promedio, 1),
                        "desviacion_ms": round(desviacion, 1),
                        "coeficiente_variacion": round(desviacion / promedio, 2),
                    }
                )

    return {
        "outliers_latencia": outliers,
        "fragmentos_score_bajo": scores_bajos[:20],
        "n_fragmentos_score_bajo": len(scores_bajos),
        "nodos_latencia_inestable": nodos_inestables,
    }


def patrones(ejecuciones: list[dict], interacciones: list[dict]) -> dict:
    """Comportamiento agregado por categoria y por tipo de tarea."""
    por_categoria: dict[str, dict] = defaultdict(lambda: {"corridas": 0, "con_error": 0, "latencias": []})
    for ej in ejecuciones:
        cat = (ej.get("input") or {}).get("categoria", "(sin categoria)") or "(sin categoria)"
        fila = por_categoria[cat]
        fila["corridas"] += 1
        fila["con_error"] += 1 if ej.get("errores") else 0
        if ej.get("latencia_total_ms"):
            fila["latencias"].append(ej["latencia_total_ms"])

    por_tarea: dict[str, Counter] = defaultdict(Counter)
    for ej in ejecuciones:
        por_tarea[ej.get("tipo_tarea") or "(sin tipo)"][ej.get("veredicto") or "(sin veredicto)"] += 1

    estados = Counter(it.get("respuesta", {}).get("estado", "?") for it in interacciones)
    return {
        "por_categoria": {
            cat: {
                "corridas": f["corridas"],
                "con_error": f["con_error"],
                "latencia_promedio_ms": round(sum(f["latencias"]) / len(f["latencias"]), 1)
                if f["latencias"]
                else 0.0,
            }
            for cat, f in sorted(por_categoria.items())
        },
        "veredictos_por_tipo_tarea": {tarea: dict(c) for tarea, c in sorted(por_tarea.items())},
        "distribucion_estados_interacciones": dict(estados),
    }


def hallazgos(
    cuellos: dict, fallas: dict, anomalias_: dict, patrones_: dict, eventos: list[dict]
) -> list[dict]:
    """Hallazgos priorizados con su evidencia numerica (base del informe IE3/IE6)."""
    hallazgos_: list[dict] = []

    if cuellos["por_nodo"]:
        top = cuellos["por_nodo"][0]
        hallazgos_.append(
            {
                "tipo": "cuello_de_botella",
                "titulo": f"El nodo '{top['nombre']}' concentra el {round(top['proporcion'] * 100)}% de la latencia del grafo",
                "evidencia": top,
            }
        )
    prop_llm = cuellos["llm_vs_resto"]["proporcion_llm"]
    hallazgos_.append(
        {
            "tipo": "cuello_de_botella",
            "titulo": f"Las llamadas al LLM representan el {round(prop_llm * 100)}% de la latencia medida en nodos",
            "evidencia": cuellos["llm_vs_resto"],
        }
    )

    for nodo, n in fallas["fallos_por_nodo"].items():
        hallazgos_.append(
            {
                "tipo": "punto_de_falla",
                "titulo": f"El nodo '{nodo}' fallo {n} vez/veces",
                "evidencia": {"nodo": nodo, "fallos": n},
            }
        )
    if fallas["reintentos"]:
        hallazgos_.append(
            {
                "tipo": "punto_de_falla",
                "titulo": f"{len(fallas['reintentos'])} corridas requirieron reintentos de pasos",
                "evidencia": fallas["reintentos"][:5],
            }
        )
    if fallas["fallbacks"]:
        por_componente = Counter(f["componente"] for f in fallas["fallbacks"])
        hallazgos_.append(
            {
                "tipo": "degradacion",
                "titulo": f"Se activaron {len(fallas['fallbacks'])} fallbacks: {dict(por_componente)}",
                "evidencia": fallas["fallbacks"][:5],
            }
        )
    if fallas["llamadas_degradadas"]:
        hallazgos_.append(
            {
                "tipo": "degradacion",
                "titulo": f"{len(fallas['llamadas_degradadas'])} llamadas al LLM degradaron a modo demo por error de la API",
                "evidencia": fallas["llamadas_degradadas"][:5],
            }
        )

    if anomalias_["outliers_latencia"]:
        hallazgos_.append(
            {
                "tipo": "anomalia",
                "titulo": f"{len(anomalias_['outliers_latencia'])} corridas con latencia outlier (> media + 2 desviaciones)",
                "evidencia": anomalias_["outliers_latencia"][:5],
            }
        )
    if anomalias_["n_fragmentos_score_bajo"]:
        hallazgos_.append(
            {
                "tipo": "anomalia",
                "titulo": f"{anomalias_['n_fragmentos_score_bajo']} fragmentos recuperados con score < {UMBRAL_SCORE_BAJO} (baja confianza del retrieval)",
                "evidencia": anomalias_["fragmentos_score_bajo"][:5],
            }
        )
    for nodo in anomalias_["nodos_latencia_inestable"]:
        hallazgos_.append(
            {
                "tipo": "anomalia",
                "titulo": f"Latencia inestable en '{nodo['nodo']}' (coef. variacion {nodo['coeficiente_variacion']})",
                "evidencia": nodo,
            }
        )

    for cat, fila in patrones_["por_categoria"].items():
        if fila["corridas"] >= 3 and fila["con_error"] > 0:
            hallazgos_.append(
                {
                    "tipo": "patron",
                    "titulo": f"La categoria '{cat}' presenta {fila['con_error']} corridas con error de {fila['corridas']}",
                    "evidencia": fila,
                }
            )

    orden = {"cuello_de_botella": 0, "punto_de_falla": 1, "degradacion": 2, "anomalia": 3, "patron": 4}
    hallazgos_.sort(key=lambda h: orden.get(h["tipo"], 9))
    return hallazgos_


def analizar(
    ruta_eventos: str = "data/eventos.jsonl",
    ruta_ejecuciones: str = "data/agente_ejecuciones.jsonl",
    ruta_interacciones: str = "data/interacciones.jsonl",
) -> dict:
    """Reporte completo de analisis de logs (estructura del informe IE3)."""
    eventos = cargar_jsonl(ruta_eventos)
    ejecuciones = cargar_jsonl(ruta_ejecuciones)
    interacciones = cargar_jsonl(ruta_interacciones)

    cuellos = cuellos_de_botella(eventos)
    fallas = puntos_de_falla(eventos, ejecuciones)
    anomalias_ = anomalias(eventos, ejecuciones, interacciones)
    patrones_ = patrones(ejecuciones, interacciones)

    return {
        "fuentes": {
            "eventos": {"ruta": ruta_eventos, "n": len(eventos)},
            "ejecuciones": {"ruta": ruta_ejecuciones, "n": len(ejecuciones)},
            "interacciones": {"ruta": ruta_interacciones, "n": len(interacciones)},
        },
        "cuellos_de_botella": cuellos,
        "puntos_de_falla": fallas,
        "anomalias": anomalias_,
        "patrones": patrones_,
        "hallazgos": hallazgos(cuellos, fallas, anomalias_, patrones_, eventos),
    }
