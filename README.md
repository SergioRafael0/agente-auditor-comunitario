# Agente Auditor Comunitario (AAC)

Agente funcional (grafo **LangGraph** con supervisor + subagentes) que integra herramientas de **consulta** (RAG sobre normativa), **razonamiento** (auditoría normativa con citas) y **escritura** (informes, correcciones de publicaciones, respuestas), con **memoria de corto plazo** (checkpointer) y **largo plazo** (experiencias auditadas en Chroma), y **planificación priorizada** con toma de decisiones adaptativa.

**Caso aplicado**: "Proveedores & Comunidades" — Evaluaciones Parciales N°1 y N°2, ISY0101 Ingeniería de Soluciones con IA, Duoc UC 2026-2.

## Modo agente (Evaluación N°2)

```bash
# Ejecutar el agente completo (grafo LangGraph) desde CLI
python -m src.grafo.cli --texto "Necesito arreglar el portón eléctrico del edificio" --categoria electricidad

# Misma conversación (memoria de corto plazo) -> reutilizar el mismo --thread-id
python -m src.grafo.cli --texto "Instalar puerta automatizada en el acceso" --categoria electricidad --thread-id demo-1

# Demo de la Evaluación 2: 5 escenarios de decisiones adaptativas con evidencia
python -m scripts.demo_agente_ev2          # outputs en data/eval/ev2/
python -m scripts.demo_agente_ev2 --num 2  # un solo escenario

# Ver la bitácora de decisiones del agente
cat data/agente_ejecuciones.jsonl
```

El grafo del agente: `planificador (supervisor)` -> `enrutador` -> subagentes (`memoria` | `consulta_normativa` | `auditoria` | `redaccion` | `guardar_memoria`) -> `finalizador`. Detalle de decisiones: `docs/decisiones-diseno-ev2.md` (IE9) y diagrama completo en `docs/diagrama-orquestacion.md` (IE8).

### Herramientas del agente (IE1)

| Tipo | Tool | Módulo |
|---|---|---|
| Consulta | `buscar_normativa()` | `src/herramientas/consulta.py` |
| Razonamiento | `auditar()` | `src/herramientas/razonamiento.py` |
| Escritura | `redactar()` (informe / revisión / respuesta) | `src/herramientas/redaccion.py` |

### Memoria (IE3)

- **Corto plazo**: checkpointer de LangGraph por `thread_id` (`src/memoria/corto_plazo.py`). Con `MEMORIA_CHECKPOINT=data/memoria/checkpoints.sqlite` persiste entre sesiones.
- **Largo plazo**: cada auditoría se guarda como experiencia en la colección Chroma `experiencias_auditoria` y se recupera por similitud en casos futuros (`src/memoria/largo_plazo.py`).

### Modo MCP (Evaluación N°1, sigue vigente)

El agente de la EV1 queda disponible como MCP server para Claude Desktop/Code (ver §"Levantar el MCP server" más abajo).

---

## Requisitos

- Python 3.11 o superior
- Git
- ~500 MB libres en disco (modelo de embeddings se descarga la primera vez)
- Una API key de Groq (gratis) — ver `docs/setup-groq.md`
- Para usar el MCP server: Claude Desktop o Claude Code

---

## Instalación paso a paso

```bash
# 1. Clonar o ubicarse en la carpeta del proyecto
cd agente-auditor-comunitario

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/Scripts/activate          # Git Bash en Windows
# .venv\Scripts\activate               # PowerShell/CMD en Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y pegar tu GROQ_API_KEY

# 5. Indexar la normativa (solo la primera vez, ~2-5 minutos)
python -m src.indexer.build_index

# 6. Probar el agente (grafo LangGraph, Evaluación N°2)
python -m src.grafo.cli --texto "Necesito arreglar el portón eléctrico del edificio" --categoria electricidad
```

---

## Configurar variables de entorno

Copiar `.env.example` a `.env` y completar. Todas las variables tienen un valor por defecto razonable salvo la API key:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx   # obligatoria (console.groq.com)
GROQ_MODEL=openai/gpt-oss-120b          # modelo de Groq
GROQ_TEMPERATURE=0.2
MCP_AUTH_TOKEN=cualquier-string-seguro  # token Bearer del MCP server
MCP_HOST=0.0.0.0
MCP_PORT=8000
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CHROMA_PATH=data/chroma
CHROMA_COLLECTION=normativa_comunidades
LOG_LEVEL=INFO                          # DEBUG | INFO | WARNING | ERROR
LOG_FILE=data/interacciones.jsonl
LOG_FILE_AGENTE=data/agente_ejecuciones.jsonl
MEMORIA_CHECKPOINT=data/memoria/checkpoints.sqlite   # vacio = memoria solo en RAM
MEMORIA_COLECCION=experiencias_auditoria
```

---

## Levantar el MCP server

```bash
python -m src.mcp_server.server
```

El server queda escuchando en `http://localhost:8000/mcp`.

### Conectar a Claude Desktop

Editar `%APPDATA%\Claude\claude_desktop_config.json` (Windows) pegando el contenido de `docs/claude_desktop_config.json` y reemplazando el token por el valor de `MCP_AUTH_TOKEN` de tu `.env`. Reiniciar Claude Desktop: la tool `revisar_publicacion` debería aparecer disponible.

### Conectar a Claude Code

```bash
claude mcp add --transport http aac http://localhost:8000/mcp --header "Authorization: Bearer tu-token-de-env"
```

Configuración completa y troubleshooting en `docs/conexion-mcp.md`.

---

## Tests

```bash
# Correr todos los tests
pytest

# Con verbosidad
pytest -v

# Solo los tests de un módulo
pytest tests/test_indexer.py -v

# Ver coverage
pytest --cov=src
```

---

## Jupyter / VS Code (recomendado para experimentar)

El venv incluye `ipykernel` y `jupyter` para usar el agente desde notebooks.

**Kernel ya registrado** como "Python (AAC)". En VS Code:

1. Instalar la extensión "Jupyter" de Microsoft (si no la tenés).
2. `Ctrl+Shift+P` → "Create: New Jupyter Notebook" (o abrí un `.ipynb` existente).
3. Arriba a la derecha, click en el selector de kernel → elegí **"Python (AAC)"**.
4. En una celda:
   ```python
   from src.agent.auditor import auditar_publicacion
   resultado = auditar_publicacion("Necesito arreglar el ascensor", "ascensor")
   resultado
   ```
5. La celda devuelve un dict con `estado`, `alertas`, `recomendaciones_generales`, etc.

**Si el kernel no aparece**, recargá VS Code (`Ctrl+Shift+P` → "Reload Window").

**Para notebook clásico de Jupyter** (no VS Code), ejecutá `jupyter notebook` en otra terminal con el venv activado. Abrí la URL que muestra (típicamente `http://localhost:8888`), creá un notebook nuevo y elegí el kernel "Python (AAC)".

---

## Estructura del proyecto

```
agente-auditor-comunitario/
├── README.md              # este archivo
├── requirements.txt       # dependencias
├── pytest.ini             # configuración de tests
├── .env.example           # plantilla de variables de entorno
├── informe.md             # informe técnico (fuente)
├── informe.pdf            # informe técnico (PDF entregable, se regenera con scripts/md_a_pdf.py)
├── data/
│   ├── normativa/         # textos legales fuente (pdf)
│   ├── eval/              # evidencia de pruebas: v1/, v2/ (prompts) y ev2/ (demo del agente)
│   ├── chunks/            # chunks procesados (gitignored)
│   ├── chroma/            # base vectorial (gitignored)
│   ├── memoria/           # checkpoints sqlite (gitignored)
│   ├── interacciones.jsonl  # log de uso del auditor (gitignored)
│   └── agente_ejecuciones.jsonl  # bitácora de ejecuciones del grafo (gitignored)
├── docs/
│   ├── setup-groq.md      # cómo sacar la API key
│   ├── conexion-mcp.md    # cómo conectar a Claude Desktop/Code
│   ├── claude_desktop_config.json  # plantilla de config para Claude Desktop
│   ├── casos-prueba.md    # publicaciones de ejemplo para testear
│   ├── decisiones-diseno-ev2.md  # justificación de componentes EV2 (IE9)
│   ├── diagrama-orquestacion.md  # diagramas de la arquitectura (IE8)
│   ├── prompts-decisiones.md  # iteración prompt v1->v2
│   ├── judge-results.md   # resultados LLM-as-judge
│   └── fuentes/           # fuentes DejaVu (para generar el PDF del informe)
├── src/
│   ├── indexer/           # ingesta -> chunks -> embeddings -> Chroma
│   ├── retriever/         # búsqueda vectorial con filtro
│   ├── agent/             # prompts + cliente Groq + núcleo auditor + judge
│   ├── herramientas/      # tools del agente: consulta, razonamiento, escritura
│   ├── memoria/           # corto plazo (checkpointer) + largo plazo (Chroma)
│   ├── grafo/             # LangGraph: planificador, enrutador, subagentes
│   ├── util/              # json_utils (parser robusto de respuestas LLM)
│   └── mcp_server/        # servidor MCP + auth
├── scripts/
│   ├── demo_agente_ev2.py # demo EV2: 5 escenarios de decisiones adaptativas
│   ├── eval_prompts.py    # batería de eval de prompts
│   ├── evaluar_con_judge.py  # LLM-as-judge sobre interacciones
│   ├── test_mcp_endpoint.py  # smoke test HTTP del MCP server
│   └── md_a_pdf.py        # genera informe.pdf desde informe.md
└── tests/                 # tests pytest (espejo de src/)
```

---

## Herramienta expuesta

### `revisar_publicacion(texto: str, categoria: str)`

Audita una publicación contra la normativa aplicable.

**Parámetros**:
- `texto` (str): descripción completa de la publicación
- `categoria` (str): una de `electricidad | ascensor | gas | agua | general | etc.`

**Devuelve** (JSON):
```json
{
  "estado": "cumple | alerta | no_cumple",
  "alertas": [
    {
      "fuente": "Ley 21.442",
      "articulo": "Artículo 17",
      "mensaje": "...",
      "recomendacion": "..."
    }
  ],
  "recomendaciones_generales": ["..."],
  "interaccion_id": "uuid"
}
```

---

## Documentación adicional

- `docs/decisiones-diseno-ev2.md`: justificación de componentes y framework EV2 (IE9)
- `docs/diagrama-orquestacion.md`: diagramas de arquitectura y flujos (IE8)
- `docs/setup-groq.md`: cómo obtener la API key de Groq
- `docs/conexion-mcp.md`: configuración y troubleshooting de conexión MCP
- `docs/casos-prueba.md`: ejemplos de publicaciones para probar
- `docs/prompts-decisiones.md`: iteración del prompt auditor v1->v2
- `docs/judge-results.md`: evaluación LLM-as-judge

---

## Licencia y atribución

Proyecto académico. Sin licencia pública por ahora.

Basado en el patrón de `mcp-asistente-curso_ejemplo` del profesor Francisco Macaya.
