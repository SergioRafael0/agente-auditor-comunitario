"""Nodo enrutador: decide el siguiente paso segun el plan y el estado.

Es el motor de la toma de decisiones adaptativa (IE7):
- Sigue el plan priorizado del planificador.
- Omite pasos que ya no aportan (ej. guardar memoria sin veredicto).
- Reintenta pasos fallados (1 reintento) y si vuelven a fallar los salta.
- Corta el ciclo si se excede el presupuesto de iteraciones.
"""

from __future__ import annotations

from src.grafo.estado import MAX_INTENTOS_POR_PASO, MAX_ITERACIONES


def enrutador(estado: dict) -> dict:
    """Determina el siguiente nodo a ejecutar y registra la decision."""
    plan: list[dict] = estado.get("plan", [])
    ejecutados: list[dict] = estado.get("pasos_ejecutados", [])
    errores: list[dict] = estado.get("errores", [])
    if estado.get("iteraciones", 0) >= MAX_ITERACIONES:
        return {
            "nodo_siguiente": "finalizador",
            "iteraciones": estado.get("iteraciones", 0) + 1,
            "bitacora": [
                {
                    "nodo": "enrutador",
                    "decision": f"Presupuesto de iteraciones agotado ({MAX_ITERACIONES}). Cierro el flujo.",
                }
            ],
        }

    for indice, paso_plan in enumerate(plan):
        nombre = paso_plan["nombre"]
        ejecuciones = [e for e in ejecutados if e.get("paso") == nombre]
        if len(ejecuciones) >= MAX_INTENTOS_POR_PASO:
            continue
        if any(e.get("ok") for e in ejecuciones):
            continue
        if len(ejecuciones) == 1 and not ejecuciones[0].get("ok"):
            decision = f"Paso '{nombre}' fallo en el intento 1: REINTENTO {len(ejecuciones) + 1}."
            return {
                "indice_paso": indice,
                "nodo_siguiente": nombre,
                "iteraciones": estado.get("iteraciones", 0) + 1,
                "bitacora": [{"nodo": "enrutador", "decision": decision}],
            }
        if nombre == "guardar_memoria" and estado.get("auditoria") is None:
            continue
        return {
            "indice_paso": indice,
            "nodo_siguiente": nombre,
            "iteraciones": estado.get("iteraciones", 0) + 1,
            "bitacora": [
                {
                    "nodo": "enrutador",
                    "decision": f"Despacho paso '{nombre}' (prioridad {paso_plan['prioridad']}): {paso_plan['justificacion']}.",
                }
            ],
        }

    return {
        "nodo_siguiente": "finalizador",
        "iteraciones": estado.get("iteraciones", 0) + 1,
        "bitacora": [{"nodo": "enrutador", "decision": "Plan completado: finalizo y redacto resumen."}],
    }


def siguiente_nodo(estado: dict) -> str:
    """Funcion de arista condicional: devuelve el nombre del nodo destino."""
    return estado.get("nodo_siguiente", "finalizador")
