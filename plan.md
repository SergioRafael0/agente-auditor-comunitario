# Plan técnico — Agente Auditor Comunitario (AAC)

Este documento detalla las decisiones técnicas con justificación.
Lo operacional (cómo trabajamos, comandos, semanas) está en `AGENTS.md`.

---

## 1. Objetivo

Construir un agente IA que audite publicaciones de la plataforma "Proveedores & Comunidades" contra normativa chilena vigente (Ley 21.442 de Copropiedad Inmobiliaria y normativas SEC aplicables), entregando alertas regulatorias concretas con citas a la fuente legal.

**Caso de uso primario:** un administrador de comunidad publica una necesidad de mantención (ej. "arreglar portón eléctrico") y antes de que proveedores le escriban, el sistema revisa automáticamente si esa publicación cumple con los requisitos normativos y avisa qué certificaciones o técnicos autorizados exige la ley.

---

## 2. Alcance MVP (Evaluación Parcial N°1, semana 7)

**Incluido:**
- Pipeline de indexación: textos normativos → chunks → embeddings → Chroma persistente
- Retrieval vectorial con filtro por categoría de publicación
- Agente que toma el texto de una publicación y devuelve:
  - Estado de cumplimiento: `cumple | alerta | no_cumple`
  - Lista de alertas regulatorias aplicables con cita exacta al artículo/numeral
  - Recomendaciones concretas para el administrador
- 1 tool MCP: `revisar_publicacion`
- MCP server local con bearer token
- Tests pytest
- Observabilidad: log de interacciones + LLM-as-judge offline
- Informe técnico 5 páginas + README ejecutable + slides

**Fuera de alcance (queda para siguientes evaluaciones del semestre):**
- Herramientas adicionales (`revisar_cotizacion`, `buscar_normativa`)
- Integración real con la app "Proveedores & Comunidades" (no existe todavía)
- Validación de cotizaciones, matching de proveedores, generación de publicaciones
- UI propia (Claude Desktop/Code es el cliente en MVP)
- Deploy en Cloud Run (local en MVP)
- Multi-tenant o auth por usuario

---

## 3. Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│ Indexer (offline, una vez o cuando cambia la normativa)     │
│                                                              │
│  data/normativa/*.txt,*.pdf                                  │
│       │                                                      │
│       ▼                                                      │
│  ingest.py (carga + limpia texto legal)                      │
│       │                                                      │
│       ▼                                                      │
│  chunk.py (split por artículo, overlap 100 tokens)           │
│       │                                                      │
│       ▼                                                      │
│  embed.py (sentence-transformers MiniLM multilingüe)         │
│       │                                                      │
│       ▼                                                      │
│  build_index.py → Chroma persistente en data/chroma/         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MCP Server (online, responde a Claude Desktop/Code)         │
│                                                              │
│  Claude Desktop/Code                                         │
│       │ streamable-http + Bearer token                       │
│       ▼                                                      │
│  src/mcp_server/server.py                                    │
│       │                                                      │
│       ▼ tool revisar_publicacion(texto, categoria)           │
│                                                              │
│  src/agent/auditor.py                                        │
│       │                                                      │
│       ├──► src/retriever/search.py (Chroma, filtro cat.)     │
│       │         │                                            │
│       │         └──► top-k chunks relevantes                 │
│       │                                                      │
│       ├──► src/agent/prompts.py (system + few-shot)          │
│       │                                                      │
│       └──► Groq API (llama-3.3-70b-versatile)                │
│                  │                                           │
│                  └──► respuesta estructurada (JSON)          │
│                                                              │
│  Log a data/interacciones.jsonl (query, respuesta, latencia) │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Decisiones técnicas por componente

### 4.1 Corpus normativo

**Qué indexar:**
- Ley 21.442 (Ley de Copropiedad Inmobiliaria) — texto completo
- 1-2 normativas SEC: ascensores (D.S. N°20/2015 aprox.) y electricidad (SEC Norma 4/2003 aprox.)
- Total estimado: ~3000-5000 chunks

**Fuente**: Biblioteca del Congreso Nacional (Ley 21.442 en texto plano), sitio oficial SEC para normativas técnicas.

**Formato**: priorizar texto plano (`.txt`) sobre PDF para evitar OCR. Si solo hay PDF, usar `pymupdf4llm` (mismo patrón que el ejemplo del curso).

**Justificación**: el mínimo viable cubre las dos áreas más críticas (mantención general en comunidades + seguridad eléctrica/ascensores). Es suficiente para demostrar el patrón RAG sin saturar al equipo ni al evaluador con demasiado corpus.

### 4.2 Chunking

**Estrategia**: split por sección natural del documento legal (artículos, títulos, capítulos), con overlap de 100 tokens entre chunks adyacentes.

**Tamaño objetivo**: 300-500 tokens por chunk (suficiente para capturar contexto de un artículo legal completo sin perder la idea por fragmentación).

**Metadata por chunk**:
- `fuente`: archivo original
- `tipo_norma`: `ley | decreto | norma_tecnica`
- `numero`: "21.442" o similar
- `articulo`: "Artículo 17" o null
- `categoria_publicacion`: tags relacionados (electricidad, ascensor, gas, agua, etc.) — permite filtrar en retrieval

**Justificación**: el texto legal tiene estructura jerárquica clara (Libro → Título → Artículo). Respetarla en el chunking preserva coherencia y permite citar exactamente.

### 4.3 Embeddings

**Modelo**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

- Dimensión: 384
- Tamaño: ~120 MB (liviano, descarga una vez)
- Soporte multilingüe (español nativo)
- Licencia Apache 2.0 (uso libre)
- Rendimiento sólido en retrieval semántico en español

**Alternativas descartadas:**
- OpenAI `text-embedding-3-small`: de pago, requiere API key adicional, rompe el principio de "MVP 100% gratis"
- Modelos más grandes (`multilingual-e5-large`): mayor precisión pero 10x más pesados, innecesarios para este corpus
- `fastembed` con ONNX: complica el setup, MiniLM es suficiente

### 4.4 Vector DB

**Elección**: Chroma en modo persistente local.

**Justificación**:
- Sin servidor que mantener (corre en proceso)
- Persistencia a disco en `data/chroma/` (sobrevive a reinicios)
- API Python simple
- Suficiente para 3000-5000 chunks (escala hasta cientos de miles sin problemas)
- Ya integrado con sentence-transformers
- Mismo paradigma que el ejemplo del profesor (que usa GCS + Parquet porque está en producción; nosotros no necesitamos esa escala)

### 4.5 LLM

**Proveedor**: Groq
**Modelo**: `llama-3.3-70b-versatile`
**Por qué este modelo**:
- Gratis hasta límites generosos (tier de desarrollo)
- Rápido (~1-2s para respuestas complejas)
- Español nativo de buena calidad
- Ventana de contexto amplia (128K tokens)
- Soporta function calling (útil si más adelante ampliamos a más tools)

**Alternativa de fallback**: `llama-3.1-8b-instant` (más rápido, menos preciso) — usar si hay rate limits.

**Temperatura**: 0.2 (queremos respuestas consistentes y reproducibles, no creativas).

**Por qué no OpenAI/Claude**: costo y dependencia de tarjeta de crédito. Groq alcanza para el alcance del MVP.

### 4.6 Prompt engineering

**System prompt** del auditor:
- Rol claro: "auditor normativo experto en Ley 21.442 y normativa SEC chilena"
- Tarea específica: analizar publicaciones y devolver JSON estructurado
- Formato de salida estricto (JSON schema)
- Reglas: no inventar normativa, citar fuente exacta, ser conservador (si duda, alertar)
- Few-shot: 1-2 ejemplos de publicación + análisis correcto

**Estructura del prompt por request**:
```
[system prompt fijo]
[contexto recuperado del RAG (top-k chunks)]
[texto de la publicación a auditar]
[schema JSON esperado]
```

**Por qué few-shot**: ayuda a que el modelo respete el formato de salida y no alucine normativa.

### 4.7 MCP server

**Patrón**: idéntico al ejemplo del profesor (`mcp-asistente-curso_ejemplo/server/`).
- SDK `mcp` Python
- Transporte `streamable-http`
- Auth bearer token (un único token compartido en MVP)
- Una sola tool: `revisar_publicacion(texto: str, categoria: str)`
- Logging a `data/interacciones.jsonl` (sin Supabase en MVP)
- `instructions` del Server que explican al LLM del cliente cuándo usar la tool

**Justificación**: replicar el patrón probado del curso. El evaluador (profesor) puede verificar fácilmente que seguimos el ejemplo.

### 4.8 Tests

**Estructura** (siguiendo ejemplo del curso):
- `tests/test_indexer.py`: ingest + chunk + embed + búsqueda básica
- `tests/test_retriever.py`: búsqueda con/sin filtro, casos vacíos
- `tests/test_auditor.py`: end-to-end con 5+ casos reales del caso "Proveedores & Comunidades"
- `tests/test_mcp_server.py`: validar schema de la tool, mock LLM

**Coverage objetivo**: ≥70% en `src/agent/` y `src/retriever/`.

**Mocks**: para tests del auditor, mockear Groq con respuestas pregrabadas (evita gastar tokens en CI).

### 4.9 Observabilidad

**Nivel 1 (incluido en MVP)**: cada llamada al agente loguea a `data/interacciones.jsonl`:
```json
{
  "timestamp": "2026-09-15T10:30:00Z",
  "tool": "revisar_publicacion",
  "input": {"texto": "...", "categoria": "electricidad"},
  "chunks_recuperados": ["Ley 21.442 Art. 17", "SEC Norma 4/2003 Sec. 3.2"],
  "respuesta": {"estado": "alerta", "alertas": [...]},
  "latencia_ms": 1850,
  "modelo": "llama-3.3-70b-versatile"
}
```

**Nivel 2 (incluido en MVP)**: script `src/agent/judge.py` que lee el JSONL y evalúa con LLM-as-judge:
- ¿Los chunks recuperados son relevantes a la publicación?
- ¿La respuesta está bien fundamentada en esos chunks?
- ¿Falta normativa que debería haberse mencionado?

**Dashboard**: leer el JSONL con cualquier herramienta (jq, pandas, Excel). Sin infra adicional en MVP.

**Justificación**: Supabase/Dashboard son mejoras para evaluaciones siguientes. JSONL local es suficiente para defender IE6 (coherencia datos↔respuestas) en la parcial.

---

## 5. Stack tecnológico final

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11+ |
| Gestor deps | pip + venv | stdlib |
| LLM API | Groq SDK | >=0.11 |
| Embeddings | sentence-transformers | >=3.0 |
| Modelo embedding | paraphrase-multilingual-MiniLM-L12-v2 | - |
| Vector DB | chromadb | >=0.5 |
| PDF parsing | pymupdf4llm | >=0.0.17 |
| PDF fallback | pypdf | >=5.0 |
| Protocol | mcp[cli] | >=1.2 |
| ASGI server | uvicorn + starlette | últimos |
| Config | python-dotenv | >=1.0 |
| Tests | pytest | >=8.0 |

---

## 6. Estructura de carpetas

```
agente-auditor-comunitario/
├── AGENTS.md                # cómo trabajamos (orden, comandos, convenciones)
├── README.md                # instrucciones para evaluadores
├── plan.md                  # este documento
├── PRESENTACION.md          # esqueleto de slides
├── .env.example             # plantilla de variables
├── .gitignore
├── requirements.txt
├── pytest.ini
├── Dockerfile               # opcional, solo si llegamos a deploy
├── data/
│   ├── normativa/           # FUENTE: textos legales (txt/pdf) — SÍ se commitea
│   ├── chunks/              # chunks procesados — gitignored
│   ├── chroma/              # base vectorial persistente — gitignored
│   └── interacciones.jsonl  # log de uso — gitignored
├── docs/
│   ├── setup-groq.md        # cómo sacar la API key
│   ├── conexion-mcp.md      # cómo conectar a Claude Desktop/Code
│   └── casos-prueba.md      # ejemplos de publicaciones para testear
├── src/
│   ├── __init__.py
│   ├── indexer/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   ├── chunk.py
│   │   ├── embed.py
│   │   └── build_index.py
│   ├── retriever/
│   │   ├── __init__.py
│   │   └── search.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   ├── prompts.py
│   │   ├── auditor.py
│   │   └── judge.py
│   └── mcp_server/
│       ├── __init__.py
│       ├── server.py
│       └── auth.py
└── tests/
    ├── __init__.py
    ├── test_indexer.py
    ├── test_retriever.py
    ├── test_auditor.py
    └── test_mcp_server.py
```

---

## 7. Roadmap por semanas

Ver `AGENTS.md` §5 para el detalle operacional. Resumen:

- **Semana 1**: setup + corpus normativo + indexación
- **Semana 2**: RAG básico CLI + boceto slides
- **Semana 3**: MCP server + tool `revisar_publicacion`
- **Semana 4**: tests + observabilidad + LLM-as-judge
- **Semana 5**: informe + slides finales + dry-run

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Groq tiene rate limit y nos quedamos sin tokens | Cachear respuestas en JSONL; usar `llama-3.1-8b-instant` como fallback |
| La Ley 21.442 es muy larga, chunks no capturan bien el contexto | Probar varios tamaños de chunk, validar con queries reales en semana 2 |
| El modelo alucina normativa inexistente | Prompt estricto con instrucción "no inventar, citar artículo exacto"; few-shot con casos reales |
| Claude Desktop no soporta `streamable-http` en la versión instalada | Documentar fallback con `stdio` en `docs/conexion-mcp.md` |
| Tiempo insuficiente para hacer todo solo | Priorizar 1 tool sobre más tools; informe puede ser 4 páginas en vez de 5 |

---

## 9. Decisiones pendientes

_(vacío por ahora — documentar aquí cualquier bifurcación que aparezca)_
