"""Dashboard de monitoreo del agente (Evaluacion 3, IE4).

Visualiza las metricas de observabilidad sobre los registros del sistema:
resumen ejecutivo, latencia por nodo y por llamada al LLM, calidad
(precision y consistencia), errores/hallazgos, explorador de trazas y uso
de recursos (tokens).

Ejecutar con:
    python -m streamlit run src/observabilidad/dashboard.py

Los datos se leen de los JSONL del sistema (rutas configurables en la
barra lateral). El boton "Recargar datos" vuelve a leer los archivos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.observabilidad import analisis, metricas

RUTAS_DEFAULT = {
    "eventos": "data/eventos.jsonl",
    "ejecuciones": "data/eval/ev3/agente_ejecuciones.jsonl",
    "interacciones": "data/interacciones.jsonl",
    "corridas": "data/eval/ev3/corridas.jsonl",
    "judge": "data/eval/judge_results.json",
}

st.set_page_config(page_title="Observabilidad AAC", page_icon="📊", layout="wide")


@st.cache_data(show_spinner=False)
def _cargar(ruta: str, _mtime: float) -> list[dict]:
    return analisis.cargar_jsonl(ruta)


def cargar_datos(rutas: dict[str, str]) -> dict[str, list[dict]]:
    datos = {}
    for clave, ruta in rutas.items():
        if clave == "judge":
            continue
        p = Path(ruta)
        datos[clave] = _cargar(ruta, p.stat().st_mtime if p.exists() else 0.0)
    return datos


def _cargar_judge(ruta: str) -> dict | None:
    p = Path(ruta)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def seccion_resumen(datos: dict) -> None:
    st.subheader("Resumen ejecutivo")
    eventos = datos["eventos"]
    ejecuciones = datos["ejecuciones"]
    corridas = datos["corridas"]

    m_lat = metricas.metricas_latencia(eventos, ejecuciones)
    m_rec = metricas.metricas_recursos(eventos)
    m_err = metricas.metricas_errores(eventos, ejecuciones)
    m_pre = metricas.metricas_precision(corridas)
    m_con = metricas.metricas_consistencia(corridas)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Precision", f"{m_pre['precision']:.0%}", help="Aciertos frente al estado esperado (corpus de pruebas)")
    c2.metric("Consistencia", f"{m_con['consistencia_global']:.0%}", help="Escenarios cuyo veredicto es estable entre re-ejecuciones")
    c3.metric("Latencia p95", f"{m_lat['latencia_total_ms']['p95']:.0f} ms", help="Percentil 95 de la latencia total por corrida")
    c4.metric("Corridas con error", f"{m_err['tasa_corridas_con_error']:.0%}", help="Proporcion de corridas con al menos un paso fallido")
    c5.metric("Tokens totales", f"{m_rec['tokens_total']:,}", help="Entrada + salida de todas las llamadas al LLM")

    st.caption(
        f"{len(ejecuciones)} corridas del grafo · {len(eventos)} eventos granulares · "
        f"{m_rec['llamadas_llm']} llamadas al LLM · {len(corridas)} corridas de benchmark"
    )

    if m_pre.get("por_variabilidad"):
        st.markdown("**Precision por tipo de variabilidad de los datos**")
        df = pd.DataFrame(
            [
                {"variabilidad": k, "precision": v["precision"], "n": v["n"]}
                for k, v in m_pre["por_variabilidad"].items()
            ]
        ).set_index("variabilidad")
        st.bar_chart(df["precision"])


def seccion_latencia(datos: dict) -> None:
    st.subheader("Latencia")
    m = metricas.metricas_latencia(datos["eventos"], datos["ejecuciones"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Por nodo del grafo (promedio ms)**")
        if m["por_nodo"]:
            df = pd.DataFrame(m["por_nodo"]).T
            st.bar_chart(df["promedio_ms"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Sin eventos de nodos.")
    with col2:
        st.markdown("**Por rol de llamada al LLM (promedio ms)**")
        if m["por_rol_llm"]:
            df = pd.DataFrame(m["por_rol_llm"]).T
            st.bar_chart(df["promedio_ms"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Sin llamadas al LLM registradas.")

    st.markdown("**Latencia total por corrida (ms)**")
    latencias = [e.get("latencia_total_ms") for e in datos["ejecuciones"] if e.get("latencia_total_ms")]
    if latencias:
        st.line_chart(pd.Series(latencias, name="latencia_total_ms"))
        t = m["latencia_total_ms"]
        st.caption(
            f"n={t['n']} · promedio={t['promedio']} ms · "
            f"p50={t['p50']:.0f} ms · p95={t['p95']:.0f} ms · max={t['max']} ms"
        )


def seccion_calidad(datos: dict, ruta_judge: str) -> None:
    st.subheader("Calidad del agente")
    m_pre = metricas.metricas_precision(datos["corridas"])
    m_con = metricas.metricas_consistencia(datos["corridas"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Precision: {m_pre['precision']:.1%}** ({m_pre['aciertos']}/{m_pre['n']} corridas)")
        if m_pre["por_variabilidad"]:
            st.dataframe(pd.DataFrame(m_pre["por_variabilidad"]).T, use_container_width=True)
    with col2:
        st.markdown(
            f"**Consistencia: {m_con['consistencia_global']:.1%}** "
            f"({m_con['escenarios_estables']}/{m_con['n_escenarios']} escenarios estables)"
        )
        if m_con["por_escenario"]:
            filas = [
                {
                    "escenario": k,
                    "estable": v["estable"],
                    "veredicto_modal": v["veredicto_modal"],
                    "n": v["n"],
                    "veredictos": json.dumps(v["veredictos"], ensure_ascii=False),
                }
                for k, v in m_con["por_escenario"].items()
            ]
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    judge = _cargar_judge(ruta_judge)
    if judge:
        st.markdown("**LLM-as-judge (calidad de las respuestas, 0.0 - 1.0)**")
        promedios = judge.get("promedios_globales", {})
        cols = st.columns(len(promedios) or 1)
        for col, (nombre, valor) in zip(cols, promedios.items()):
            col.metric(nombre, f"{valor:.3f}" if valor is not None else "n/d")

    st.markdown("**Detalle de corridas de benchmark**")
    if datos["corridas"]:
        df = pd.DataFrame(datos["corridas"])
        columnas = [
            c
            for c in (
                "escenario", "variabilidad", "modo_solicitado", "repeticion",
                "estado_obtenido", "estados_esperados", "acierto",
                "latencia_total_ms", "tokens_entrada", "tokens_salida",
            )
            if c in df.columns
        ]
        st.dataframe(df[columnas], use_container_width=True, hide_index=True)
    else:
        st.info("Sin corridas de benchmark. Ejecuta `python -m scripts.benchmark_observabilidad`.")


def seccion_errores(datos: dict, rutas: dict[str, str]) -> None:
    st.subheader("Errores, fallas y hallazgos")
    reporte = analisis.analizar(
        rutas["eventos"], rutas["ejecuciones"], rutas["interacciones"]
    )
    st.markdown(f"**{len(reporte['hallazgos'])} hallazgos detectados**")
    for h in reporte["hallazgos"]:
        icono = {"cuello_de_botella": "⏱", "punto_de_falla": "⚠", "degradacion": "⬇", "anomalia": "🔍", "patron": "📈"}.get(h["tipo"], "•")
        st.markdown(f"- {icono} **[{h['tipo']}]** {h['titulo']}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Fallbacks y degradaciones**")
        fallas = reporte["puntos_de_falla"]
        filas = fallas["fallbacks"] + [
            {"componente": f"llm:{d['rol']}", "detalle": d["error"], "trace_id": d["trace_id"]}
            for d in fallas["llamadas_degradadas"]
        ]
        if filas:
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
        else:
            st.success("Sin fallbacks registrados.")
    with col2:
        st.markdown("**Corridas con errores**")
        if reporte["puntos_de_falla"]["corridas_con_error"]:
            st.dataframe(
                pd.DataFrame(reporte["puntos_de_falla"]["corridas_con_error"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Sin errores registrados en las corridas.")


def seccion_trazas(datos: dict) -> None:
    st.subheader("Explorador de trazas")
    ejecuciones = [e for e in datos["ejecuciones"] if e.get("trace_id")]
    if not ejecuciones:
        st.info("Sin trazas registradas. Ejecuta el agente o el benchmark primero.")
        return

    opciones = {f"{e['trace_id'][:8]} · {e.get('tipo_tarea', '?')} · {e.get('latencia_total_ms', 0)} ms": e for e in ejecuciones}
    elegida = st.selectbox("Traza", list(opciones.keys()))
    ejecucion = opciones[elegida]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Ejecucion**")
        st.json(
            {
                "trace_id": ejecucion.get("trace_id"),
                "thread_id": ejecucion.get("thread_id"),
                "input": ejecucion.get("input"),
                "tipo_tarea": ejecucion.get("tipo_tarea"),
                "plan": ejecucion.get("plan"),
                "veredicto": ejecucion.get("veredicto"),
                "latencia_total_ms": ejecucion.get("latencia_total_ms"),
                "llm": ejecucion.get("llm"),
            }
        )
    with col2:
        st.markdown("**Pasos ejecutados**")
        if ejecucion.get("pasos_detalle"):
            st.dataframe(pd.DataFrame(ejecucion["pasos_detalle"]), use_container_width=True, hide_index=True)
        st.markdown("**Bitacora de decisiones**")
        for b in ejecucion.get("bitacora", []):
            st.markdown(f"- `{b.get('nodo', '')}` {b.get('decision', '')}")

    st.markdown("**Eventos granulares de la traza**")
    eventos = [e for e in datos["eventos"] if e.get("trace_id") == ejecucion.get("trace_id")]
    if eventos:
        st.dataframe(pd.DataFrame(eventos), use_container_width=True, hide_index=True)
    else:
        st.caption("Sin eventos granulares para esta traza.")


def seccion_recursos(datos: dict) -> None:
    st.subheader("Uso de recursos (tokens)")
    m = metricas.metricas_recursos(datos["eventos"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Llamadas al LLM", m["llamadas_llm"])
    c2.metric("Tokens de entrada", f"{m['tokens_entrada_total']:,}")
    c3.metric("Tokens de salida", f"{m['tokens_salida_total']:,}")
    c4.metric("Promedio por llamada", f"{m['tokens_promedio_por_llamada']:,.0f}")

    if m["por_rol"]:
        st.markdown("**Tokens por rol de llamada**")
        df = pd.DataFrame(m["por_rol"]).T
        st.bar_chart(df[["tokens_entrada", "tokens_salida"]])
        st.dataframe(df, use_container_width=True)

    st.caption(
        f"Proporcion de tokens estimados (modo demo/simulado): {m['proporcion_tokens_estimados']:.0%}. "
        "Los tokens reales provienen del uso reportado por la API de Groq."
    )

    st.markdown("**Tokens por corrida de benchmark**")
    if datos["corridas"]:
        df = pd.DataFrame(datos["corridas"])
        if "tokens_entrada" in df.columns:
            st.line_chart(df[["tokens_entrada", "tokens_salida"]])


def main() -> None:
    st.title("Agente Auditor Comunitario — Observabilidad")

    with st.sidebar:
        st.header("Configuracion")
        rutas = {}
        for clave, valor in RUTAS_DEFAULT.items():
            rutas[clave] = st.text_input(clave, value=valor)
        if st.button("Recargar datos"):
            st.cache_data.clear()
        seccion = st.radio(
            "Seccion",
            ["Resumen", "Latencia", "Calidad", "Errores y hallazgos", "Trazas", "Recursos"],
        )

    datos = cargar_datos(rutas)
    if seccion == "Resumen":
        seccion_resumen(datos)
    elif seccion == "Latencia":
        seccion_latencia(datos)
    elif seccion == "Calidad":
        seccion_calidad(datos, rutas["judge"])
    elif seccion == "Errores y hallazgos":
        seccion_errores(datos, rutas)
    elif seccion == "Trazas":
        seccion_trazas(datos)
    else:
        seccion_recursos(datos)


if __name__ == "__main__":
    main()
