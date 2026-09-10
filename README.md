# Agente Auditor Comunitario (AAC)

MCP server con RAG que audita publicaciones de comunidades contra la Ley 21.442 (Copropiedad Inmobiliaria) y normativa SEC chilena, devolviendo alertas regulatorias concretas con citas a la fuente legal.

**Caso aplicado**: "Proveedores & Comunidades" — Evaluación Parcial N°1, ISY0101 Ingeniería de Soluciones con IA, Duoc UC 2026-2.

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

# 6. Probar el agente en CLI
python -m src.agent.auditor --texto "Necesito arreglar el portón eléctrico del edificio" --categoria electricidad
```

---

## Configurar variables de entorno

Editar `.env`:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
MCP_AUTH_TOKEN=cualquier-string-seguro
LOG_LEVEL=INFO
```

- `GROQ_API_KEY`: tu API key de console.groq.com
- `MCP_AUTH_TOKEN`: token compartido que pedirá el MCP server a Claude (en MVP es solo uno, no por usuario)
- `LOG_LEVEL`: `DEBUG | INFO | WARNING | ERROR`

---

## Levantar el MCP server

```bash
python -m src.mcp_server.server
```

El server queda escuchando en `http://localhost:8000/mcp`.

### Conectar a Claude Desktop

Editar `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "aac": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer tu-token-de-env"
      }
    }
  }
}
```

Reiniciar Claude Desktop. La tool `revisar_publicacion` debería aparecer disponible.

### Conectar a Claude Code

```bash
claude mcp add --transport http aac http://localhost:8000/mcp --header "Authorization: Bearer tu-token-de-env"
```

Ver `docs/conexion-mcp.md` para más detalle y troubleshooting.

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

## Estructura del proyecto

```
agente-auditor-comunitario/
├── AGENTS.md              # cómo trabajamos (orden, comandos, convenciones)
├── README.md              # este archivo
├── plan.md                # decisiones técnicas con justificación
├── PRESENTACION.md        # esqueleto de slides para la defensa
├── data/
│   ├── normativa/         # textos legales fuente (txt/pdf)
│   ├── chunks/            # chunks procesados (gitignored)
│   ├── chroma/            # base vectorial (gitignored)
│   └── interacciones.jsonl  # log de uso (gitignored)
├── docs/
│   ├── setup-groq.md      # cómo sacar la API key
│   ├── conexion-mcp.md    # cómo conectar a Claude Desktop/Code
│   └── casos-prueba.md    # publicaciones de ejemplo para testear
├── src/
│   ├── indexer/           # ingesta → chunks → embeddings → Chroma
│   ├── retriever/         # búsqueda vectorial con filtro
│   ├── agent/             # prompts + cliente Groq + lógica del auditor
│   └── mcp_server/        # servidor MCP + auth
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

- `plan.md`: decisiones técnicas detalladas
- `AGENTS.md`: forma de trabajo del proyecto
- `PRESENTACION.md`: slides para la defensa
- `docs/setup-groq.md`: cómo obtener la API key de Groq
- `docs/conexion-mcp.md`: troubleshooting de conexión MCP
- `docs/casos-prueba.md`: ejemplos de publicaciones para probar

---

## Licencia y atribución

Proyecto académico. Sin licencia pública por ahora.

Basado en el patrón de `mcp-asistente-curso_ejemplo` del profesor Francisco Macaya.
