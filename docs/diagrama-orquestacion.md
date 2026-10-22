# Diagramas de orquestación — Agente Auditor Comunitario (IE8)

## 1. Diagrama general de orquestación (LangGraph)

```mermaid
flowchart TD
    U["Solicitud del usuario<br/>(publicacion + categoria)"] --> S["START"]
    S --> P["planificador<br/>supervisor - decide tipo de tarea y plan priorizado"]
    P --> E{"enrutador<br/>despacha paso siguiente<br/>decisiones adaptativas"}

    E -->|memoria| M["subagente memoria<br/>recupera experiencias<br/>de largo plazo"]
    E -->|consulta_normativa| C["subagente consulta<br/>RAG / buscar_normativa"]
    E -->|auditoria| A["subagente auditor<br/>auditar - veredicto + citas"]
    E -->|redaccion| W["subagente redactor<br/>redactar - 3 modos"]
    E -->|guardar_memoria| G["guardar experiencia<br/>en Chroma"]
    E -->|plan completo / limite| R["finalizador<br/>resumen trazable"]

    M --> E
    C --> E
    A --> E
    W --> E
    G --> E
    R --> END2("END")

    A -. "historial de veredictos<br/>via checkpointer" .-> CP["memoria corto plazo"]
    G -. "experiencias" .-> LP["memoria largo plazo<br/>coleccion experiencias_auditoria"]
    M -. "lee experiencias" .-> LP
```

## 2. Flujo de trabajo organizacional resuelto

Caso: administrador de comunidad publica una necesidad de mantención.

```mermaid
flowchart LR
    A["Administrador publica<br/>necesidad de mantencion"] --> B["Agente planifica<br/>tipo de tarea + pasos"]
    B --> C1{"Publicacion clara?"}
    C1 -->|No| D1["Redactor propone<br/>publicacion corregida"]
    D1 --> D2["Administrador revisa<br/>y re-publica"]
    C1 -->|Si| D3["Auditor evalua contra<br/>Ley 21.442 + RIC SEC"]
    D3 --> E1["Informe con citas legales<br/>para la asamblea/proveedores"]
    D3 -.-> F1["Experiencia guardada<br/>para auditorias futuras"]
```

## 3. Secuencia de una ejecución (con memoria)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant G as Grafo LangGraph
    participant M as Memoria corto plazo (checkpointer)
    participant ML as Memoria largo plazo (Chroma)
    participant L as Groq LLM

    U->>G: publicacion + categoria (thread_id)
    G->>L: planificar (JSON de pasos priorizados)
    L-->>G: plan = memoria, auditoria, redaccion, guardar_memoria
    G->>M: checkpoint tras cada nodo
    G->>ML: buscar_experiencias(publicacion)
    ML-->>G: 0..3 experiencias similares
    G->>G: subagente auditor (RAG + LLM)
    G->>G: subagente redactor (modo segun veredicto)
    G->>ML: guardar_experiencia(veredicto)
    G-->>U: respuesta final + bitacora de decisiones
    Note over U,M: Turno siguiente con mismo thread_id:<br/>el estado previo continua disponible
```

## 4. Arquitectura de módulos (capas)

```
┌────────────────────────────────────────────────────────────┐
│ INTERFACES                                                  │
│   CLI (src/grafo/cli.py)             MCP server (EV1)       │
├────────────────────────────────────────────────────────────┤
│ ORQUESTACION (LangGraph)                                    │
│   src/grafo/grafo.py      StateGraph + aristas condicionales│
│   src/grafo/planificador.py   plan LLM + heuristica fallback│
│   src/grafo/enrutador.py      despacho + reintentos         │
│   src/grafo/subagentes.py     1 subagente por herramienta   │
├────────────────────────────────────────────────────────────┤
│ HERRAMIENTAS (IE1)                                          │
│   consulta.py (RAG)   razonamiento.py (auditar)   escritura │
├────────────────────────────────────────────────────────────┤
│ MEMORIA (IE3)                                               │
│   corto_plazo.py (checkpointer)   largo_plazo.py (Chroma)   │
├────────────────────────────────────────────────────────────┤
│ BASE (EV1, sin cambios)                                     │
│   retriever (Chroma+MiniLM)   llm.py (Groq)   prompts.py v2 │
│   indexer (ingesta->chunks->embeddings->build_index)        │
└────────────────────────────────────────────────────────────┘
```

## 5. Evidencias

- Bitácora real de 5 escenarios: `data/eval/ev2/` (generada con `python -m scripts.demo_agente_ev2`).
- Logs de ejecución por paso: `data/agente_ejecuciones.jsonl`.
- Tests del grafo, memoria y herramientas: `tests/test_grafo.py`, `tests/test_memoria.py`, `tests/test_herramientas.py`.
