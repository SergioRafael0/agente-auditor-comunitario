# Agente Auditor Comunitario (AAC)

Agente que audita publicaciones de mantención de edificios ("Proveedores & Comunidades") contra la normativa chilena vigente (Ley 21.442 y normas SEC). Recibe la descripción de un trabajo y devuelve un veredicto con alertas, citas a la fuente legal y recomendaciones.

Está armado como un grafo **LangGraph**: un planificador prioriza los pasos, un enrutador despacha subagentes (memoria, consulta normativa, auditoría, redacción), y hay memoria de corto y largo plazo. Se usa desde la terminal, desde Jupyter o como herramienta MCP en Claude Desktop/Code.

Evaluaciones Parciales N°1 y N°2 — ISY0101 Ingeniería de Soluciones con IA, Duoc UC 2026-2.

---

## Probarlo sin API key (modo demo)

El agente funciona **sin ninguna clave**: el LLM se simula con respuestas de demostración y todo lo demás (planificación, enrutador, memoria, herramientas) corre de verdad.

```bash
# Grafo completo en modo demo
python -m src.grafo.cli --texto "Necesito instalar un tablero electrico en el edificio" \
    --categoria electricidad --demo

# Publicacion vaga -> el agente pide los datos que faltan (no inventa nada)
python -m src.grafo.cli --texto "Necesito ayuda con unas cosas del edificio" \
    --categoria general --demo
```

Otras formas de probarlo sin clave:

- `pytest` — 58 tests en verde (todos con LLM mockeado).
- `data/eval/ev2/` — corridas reales del agente (5 escenarios con bitácora).
- `demo.ipynb` — los mismos ejemplos celda por celda; sin key arranca solo en modo demo.

Con API key (gratis en console.groq.com) las respuestas son reales: solo hay que pegarla en `.env`. Si la clave falla a mitad de una corrida, el agente degrada al modo demo en vez de romperse.

---

## Instalación

```bash
cd agente-auditor-comunitario

python -m venv .venv
source .venv/Scripts/activate        # Git Bash en Windows
# .venv\Scripts\activate             # PowerShell/CMD

pip install -r requirements.txt

cp .env.example .env                 # completar GROQ_API_KEY (opcional en modo demo)

python -m src.indexer.build_index    # indexa la normativa (~2-5 min, solo la primera vez)
```

---

## Comandos principales

```bash
# Agente completo (grafo LangGraph)
python -m src.grafo.cli --texto "Necesito arreglar el porton electrico del edificio" --categoria electricidad

# Misma conversacion (memoria de corto plazo): repetir el mismo --thread-id
python -m src.grafo.cli --texto "El porton es basculante de 400 kg" --categoria electricidad --thread-id demo-1

# Auditoria simple (sin grafo, herramienta revisar_publicacion)
python -m src.agent.auditor --texto "Necesito arreglar el ascensor" --categoria ascensor

# Demo con 5 escenarios de decisiones adaptativas (guarda evidencia en data/eval/ev2/)
python -m scripts.demo_agente_ev2

# Tests
pytest
```

Agregar `--demo` a cualquier comando para correr sin API key.

---

## MCP server (Claude Desktop / Code)

```bash
python -m src.mcp_server.server     # queda en http://localhost:8000/mcp
```

Expone la herramienta `revisar_publicacion(texto, categoria)`. La configuración para conectarlo a Claude Desktop o Claude Code está en `docs/conexion-mcp.md` (incluye la plantilla `docs/claude_desktop_config.json`).

---

## Qué hay dentro

- `src/grafo/` — grafo LangGraph: planificador, enrutador con aristas condicionales, subagentes y finalizador.
- `src/herramientas/` — las 3 tools del agente: consulta (RAG), razonamiento (auditar) y escritura (redactar).
- `src/memoria/` — corto plazo (checkpointer por `thread_id`) y largo plazo (experiencias en Chroma).
- `src/indexer/` — pasa los PDF de `data/normativa/` a chunks con embeddings en Chroma.
- `src/retriever/` — búsqueda semántica con filtros.
- `src/agent/` — cliente Groq (con modo demo), prompts del auditor y LLM-as-judge.
- `src/mcp_server/` — servidor MCP con autenticación.
- `tests/` — 58 tests pytest (mockean LLM y Chroma).
- `scripts/` — demo, evaluación de prompts y smoke test del MCP.
- `data/eval/` — evidencia de corridas reales.

Más detalle de diseño: `docs/decisiones-diseno-ev2.md`. Diagramas: `docs/diagrama-orquestacion.md`.

---

## Variables de entorno

Ver `.env.example`. Las únicas importantes al empezar:

- `GROQ_API_KEY` — opcional en modo demo; con ella las respuestas son reales.
- `MCP_AUTH_TOKEN` — token que exige el MCP server.
- `LLM_MODO=offline` — fuerza el modo demo aunque haya key.

---

## Licencia y atribución

Proyecto académico. Sin licencia pública por ahora.

Basado en el patrón de `mcp-asistente-curso_ejemplo` del profesor Francisco Macaya.
