"""Motor de metricas de observabilidad (Evaluacion 3, IE1 e IE2).

Calcula sobre los registros del sistema las cinco metricas del encargo:

- Precision: aciertos frente a los estados esperados del corpus de pruebas.
- Consistencia: estabilidad del veredicto ante re-ejecuciones del mismo input.
- Frecuencia de errores: fallos por nodo, reintentos y degradaciones (fallbacks).
- Latencia: percentiles p50/p95 totales, por nodo del grafo y por llamada al LLM.
- Uso de recursos: tokens de entrada/salida (reales de la API o estimados).

Las funciones aceptan los registros ya cargados (listas de dicts), de modo
que las usan tanto el benchmark (`scripts/benchmark_observabilidad.py`) como
el analisis de logs (`scripts/analizar_logs.py`) y el dashboard.
"""

from __future__ import annotations

from collections import Counter, defaultdict


def percentil(valores: list[float], p: float) -> float:
    """Percentil p (0-100) de una lista de numeros (interpolacion lineal)."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return float(ordenados[0])
    k = (len(ordenados) - 1) * (p / 100)
    inferior = int(k)
    superior = min(inferior + 1, len(ordenados) - 1)
    return float(ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * (k - inferior))


def metricas_latencia(eventos: list[dict], ejecuciones: list[dict]) -> dict:
    """Latencia total, por nodo del grafo y por rol de llamada al LLM."""
    nodos = defaultdict(list)
    llm_por_rol = defaultdict(list)
    for e in eventos:
        if e.get("evento") == "nodo":
            nodos[e.get("nodo", "?")].append(e.get("latencia_ms", 0))
        elif e.get("evento") == "llm_llamada":
            llm_por_rol[e.get("rol", "?")].append(e.get("latencia_ms", 0))

    totales = [ej.get("latencia_total_ms", 0) for ej in ejecuciones if ej.get("latencia_total_ms") is not None]
    return {
        "latencia_total_ms": {
            "n": len(totales),
            "promedio": _promedio(totales),
            "p50": percentil(totales, 50),
            "p95": percentil(totales, 95),
            "max": max(totales) if totales else 0,
        },
        "por_nodo": {
            nombre: {
                "ejecuciones": len(vals),
                "promedio_ms": _promedio(vals),
                "p95_ms": percentil(vals, 95),
            }
            for nombre, vals in sorted(nodos.items())
        },
        "por_rol_llm": {
            rol: {
                "llamadas": len(vals),
                "promedio_ms": _promedio(vals),
                "p95_ms": percentil(vals, 95),
            }
            for rol, vals in sorted(llm_por_rol.items())
        },
    }


def metricas_recursos(eventos: list[dict]) -> dict:
    """Consumo de tokens por llamada y por rol, reales vs estimados."""
    llamadas = [e for e in eventos if e.get("evento") == "llm_llamada"]
    entrada = [e.get("tokens_entrada", 0) for e in llamadas]
    salida = [e.get("tokens_salida", 0) for e in llamadas]
    por_rol = defaultdict(lambda: {"llamadas": 0, "tokens_entrada": 0, "tokens_salida": 0})
    for e in llamadas:
        rol = por_rol[e.get("rol", "?")]
        rol["llamadas"] += 1
        rol["tokens_entrada"] += e.get("tokens_entrada", 0) or 0
        rol["tokens_salida"] += e.get("tokens_salida", 0) or 0
    return {
        "llamadas_llm": len(llamadas),
        "tokens_entrada_total": sum(entrada),
        "tokens_salida_total": sum(salida),
        "tokens_total": sum(entrada) + sum(salida),
        "tokens_promedio_por_llamada": _promedio([a + b for a, b in zip(entrada, salida)]),
        "proporcion_tokens_estimados": (
            round(sum(1 for e in llamadas if e.get("tokens_estimados")) / len(llamadas), 3)
            if llamadas
            else 0.0
        ),
        "por_rol": dict(por_rol),
    }


def metricas_errores(eventos: list[dict], ejecuciones: list[dict]) -> dict:
    """Frecuencia de errores: nodos fallidos, fallbacks y corridas con fallos."""
    nodos = [e for e in eventos if e.get("evento") == "nodo"]
    fallos_nodo = Counter(e.get("nodo", "?") for e in nodos if not e.get("ok"))
    fallbacks = Counter(
        e.get("componente", "?") for e in eventos if e.get("evento") == "fallback"
    )
    llamadas = [e for e in eventos if e.get("evento") == "llm_llamada"]
    degradadas = sum(1 for e in llamadas if e.get("degradada"))
    corridas_con_error = sum(1 for ej in ejecuciones if ej.get("errores"))
    return {
        "nodos_ejecutados": len(nodos),
        "nodos_fallidos": sum(fallos_nodo.values()),
        "fallos_por_nodo": dict(fallos_nodo),
        "fallbacks_por_componente": dict(fallbacks),
        "llamadas_llm_degradadas": degradadas,
        "corridas_con_error": corridas_con_error,
        "tasa_corridas_con_error": (
            round(corridas_con_error / len(ejecuciones), 3) if ejecuciones else 0.0
        ),
    }


def metricas_precision(corridas: list[dict]) -> dict:
    """Aciertos frente al estado esperado, global y por tipo de variabilidad."""
    validas = [c for c in corridas if c.get("estados_esperados")]
    if not validas:
        return {"n": 0, "aciertos": 0, "precision": 0.0, "por_variabilidad": {}}
    aciertos = sum(1 for c in validas if c.get("acierto"))
    por_var: dict[str, list[bool]] = defaultdict(list)
    for c in validas:
        por_var[c.get("variabilidad", "otra")].append(bool(c.get("acierto")))
    return {
        "n": len(validas),
        "aciertos": aciertos,
        "precision": round(aciertos / len(validas), 3),
        "por_variabilidad": {
            nombre: {
                "n": len(vals),
                "aciertos": sum(vals),
                "precision": round(sum(vals) / len(vals), 3),
            }
            for nombre, vals in sorted(por_var.items())
        },
    }


def metricas_consistencia(corridas: list[dict]) -> dict:
    """Estabilidad del veredicto ante re-ejecuciones del mismo escenario."""
    por_escenario: dict[str, list[str]] = defaultdict(list)
    for c in corridas:
        if c.get("estados_esperados"):
            por_escenario[c.get("escenario", "?")].append(c.get("estado_obtenido") or "(sin veredicto)")
    if not por_escenario:
        return {"n_escenarios": 0, "consistencia_global": 0.0, "por_escenario": {}}
    detalle = {}
    estables = 0
    for escenario, veredictos in sorted(por_escenario.items()):
        conteo = Counter(veredictos)
        moda, repeticiones = conteo.most_common(1)[0]
        estable = repeticiones == len(veredictos)
        estables += estable
        detalle[escenario] = {
            "n": len(veredictos),
            "veredictos": dict(conteo),
            "veredicto_modal": moda,
            "estable": estable,
        }
    return {
        "n_escenarios": len(por_escenario),
        "escenarios_estables": estables,
        "consistencia_global": round(estables / len(por_escenario), 3),
        "por_escenario": detalle,
    }


def calcular_resumen(corridas: list[dict], eventos: list[dict], ejecuciones: list[dict]) -> dict:
    """Resumen completo de las cinco metricas para guardar como evidencia."""
    return {
        "precision": metricas_precision(corridas),
        "consistencia": metricas_consistencia(corridas),
        "errores": metricas_errores(eventos, ejecuciones),
        "latencia": metricas_latencia(eventos, ejecuciones),
        "recursos": metricas_recursos(eventos),
    }


def _promedio(valores: list[float]) -> float:
    return round(sum(valores) / len(valores), 1) if valores else 0.0
