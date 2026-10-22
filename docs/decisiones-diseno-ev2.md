# Decisiones de diseño — Evaluación N°2 (IE9)

Este documento justifica cada componente del agente para la Evaluación 2,
mostrando la alineación entre herramientas, framework, memoria y los
requerimientos del flujo de trabajo organizacional ("Proveedores & Comunidades").

La justificación del stack de base (LLM Groq, embeddings, Chroma, chunking)
corresponde a la Evaluación 1 y se describe en el `README.md` y en el código de
`src/indexer/`, `src/retriever/` y `src/agent/`. Aquí se documenta lo nuevo.

---

## Resumen de decisiones

| Requerimiento del flujo | Componente elegido | Por qué este y no otro |
|---|---|---|
| El agente debe decidir qué hacer con autonomía (IE1) | Grafo LangGraph con supervisor + subagentes | Un pipeline fijo (EV1) no decide nada: hace siempre lo mismo. Con aristas condicionales el *routing* cambia según el estado, lo que entrega comportamiento adaptativo verificable. |
| Framework de agentes (IE2) | `langgraph` (ecosistema LangChain) | Indicado explícitamente por el docente. Soporta memoria vía checkpointer, subgrafos y aristas condicionales. Haystack usa pipelines rígidos, medio similar al de la EV1; Autogen genera conversaciones multi-LLM más costosas. |
| Memoria corto plazo (IE3) | Checkpointer de LangGraph (`MemorySaver`/`SqliteSaver`) por `thread_id` | Permite continuidad de conversaciones multi-turno sin infraestructura externa. Sqlite opcional para persistencia entre sesiones. |
| Memoria largo plazo (IE3) | Colección Chroma `experiencias_auditoria` | Reutiliza el código de embeddings ya validado en la EV1: cada auditoría queda como experiencia y se recupera por similitud semántica en tareas futuras. |
| Recuperación semántica (IE4) | `src/retriever/search.py` (EV1, sin cambios) | Ya validado: 312 chunks, fallback del filtro por categoría de Chroma, citas correctas. Reutilizar reduce riesgo. |
| Herramientas (IE1) | 3 tipos: consulta (`buscar_normativa`), razonamiento (`auditar`), escritura (`redactar`, 3 modos) | La rúbrica exige integrar los tres tipos. La escritura cambia de modo (`informe_auditoria`/`proponer_revision`/`respuesta_consulta`) según el estado, lo que es a la vez decisión adaptativa. |
| Planificación (IE5) | Nodo `planificador`: LLM emite JSON de pasos priorizados; respaldo heurístico determinístico | Un plan con prioridades numeradas (1..4) es defendible en IE5. Heurística de respaldo garantiza que el flujo nunca se bloquee por fallo del LLM. |
| Trazabilidad (IE6, IE7) | Bitácora por paso + logs JSONL + evidencias en `data/eval/ev2/` | Cada decisión queda registrada con su justificación, lo que permite reconstruir el comportamiento del agente para el informe y la demo. |

---

## El grafo (por qué supervisor + subagentes)

El diagrama del grafo (nodos, aristas condicionales y flujos) vive en `docs/diagrama-orquestacion.md`, que es la referencia canónica de arquitectura de este proyecto. Aquí solo se justifica el patrón elegido.

**Por qué este patrón y no un agente único ReAct:**

1. **Escalabilidad (IE2)**: agregar un subagente nuevo (p. ej. `revisar_cotizacion`, previsto para próximas iteraciones) es registrar una tool en `NODOS_PASO`; no se toca el enrutador ni el estado.
2. **Trazabilidad**: cada paso es un nodo con tool única, lo que produce una bitácora legible para el informe y la demo en vivo.
3. **Costo y latencia**: cada subagente usa un prompt corto, versus un ReAct que envía todas las tools y todo el contexto en cada iteración (con Groq esto se nota: cada llamada del auditor ya toma ~25-30 s con el contexto RAG completo).

---

## Toma de decisiones adaptativa (IE7) — reglas concretas

1. **Reintento ante fallo**: si un subagente lanza excepción, el enrutador re-despacha el mismo paso una vez (`MAX_INTENTOS_POR_PASO = 2`). Si vuelve a fallar, lo salta y el finalizador reporta el error sin colapsar.
2. **Publicación vaga → revisión en vez de informe**: si el auditor devuelve `no_cumple` sin alertas técnicas, o el texto es muy corto o pide "ayuda", el redactor cambia a modo `proponer_revision` (reescribe la publicación de forma que sí sea útil para proveedores).
3. **Ruta según tipo de tarea**: pregunta sobre normativa despliega `consulta_normativa` + respuesta redactada; trabajo concreto despliega `auditoria` + informe. El planificador LLM decide con criterio estricto en el prompt; si falla, aplica la heurística por regex.
4. **LLM del planificador indisponible**: se degrada a plan heurístico determinístico y el flujo completo sigue funcionando.
5. **Primera ejecución sin experiencias**: `buscar_experiencias()` devuelve colección vacía y los prompts usan "(sin experiencias previas)" — el sistema no depende de que la memoria esté poblada.

Estas decisiones están evidenciadas en `data/eval/ev2/*.json` (bitácora por escenario, corrida real con Groq).

---

## Herramientas (IE1)

| Tipo (rúbrica) | Herramienta | Módulo | Qué hace |
|---|---|---|---|
| Consulta | `buscar_normativa()` | `src/herramientas/consulta.py` | RAG sobre la normativa (Ley 21.442 + RIC SEC); reutiliza `src/retriever/search.py` de la EV1 |
| Razonamiento | `auditar()` | `src/herramientas/razonamiento.py` | Núcleo EV1 (RAG + LLM con prompt v2 y few-shots); devuelve veredicto con citas legales |
| Escritura | `redactar()` | `src/herramientas/redaccion.py` | Genera informe de auditoría, revisión de publicación vaga o respuesta normativa (3 modos, JSON validado) |

---

## Memoria (IE3)

**Corto plazo** — `src/memoria/corto_plazo.py`:
- Checkpointer de LangGraph que persiste el estado del grafo tras cada nodo.
- `thread_id` agrupa la conversación: en turnos sucesivos del mismo hilo, el historial y las decisiones previas siguen disponibles vía checkpointer.
- Con `MEMORIA_CHECKPOINT=ruta.sqlite` persiste entre ejecuciones (reanudar tareas interrumpidas).

**Largo plazo** — `src/memoria/largo_plazo.py`:
- Cada auditoría completada guarda {texto, categoria, veredicto} en la colección Chroma `experiencias_auditoria`.
- En casos nuevos, `buscar_experiencias()` retorna las 3 más similares por embeddings y las inyecta en los prompts (redactor) y bitácora.
- Evidencia: escenario 4 de `data/eval/ev2/` recupera `experiencias_previas >= 1` de ejecuciones anteriores.

---

## Referencias de frameworks usados en esta iteración

- LangGraph (ecosistema LangChain): https://langchain-ai.github.io/langgraph/
- Persistencia y checkpoints de LangGraph: https://langchain-ai.github.io/langgraph/concepts/persistence/
- Groq API (SDK Python): https://console.groq.com/docs
- Chroma DB: https://docs.trychroma.com/
- sentence-transformers: https://www.sbert.net/
