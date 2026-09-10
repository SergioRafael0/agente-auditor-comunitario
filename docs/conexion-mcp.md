# Conexión MCP — Claude Desktop / Claude Code

Cómo conectar el Agente Auditor Comunitario a tu cliente MCP.

## 0. Verificar que el server funciona (sin Claude Desktop)

Antes de conectar un cliente, puedes verificar que el server MCP responde correctamente:

```bash
python -m scripts.test_mcp_endpoint
```

Esto lanza el server en un thread, hace las 3 peticiones JSON-RPC del protocolo MCP (initialize, tools/list, tools/call con un caso real) y muestra la respuesta. Tambien guarda la salida completa en `data/eval/mcp_endpoint_demo.json` como evidencia.

Salida esperada:
- `Status: 200` en las 3 peticiones
- Session ID devuelto
- Tool `revisar_publicacion` listada
- Respuesta del agente con `estado: alerta` y citas a la Ley 21.442

---

## 1. Levantar el server

En una terminal:

```bash
cd agente-auditor-comunitario
source .venv/Scripts/activate          # Git Bash
python -m src.mcp_server.server
```

Deberías ver algo como:

```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

El server queda escuchando en `http://localhost:8000/mcp`. **No cierres esta terminal** mientras uses el agente desde Claude.

---

## 2. Conectar a Claude Desktop

### Ubicación del archivo de configuración

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
  - Típicamente: `C:\Users\<tu-usuario>\AppData\Roaming\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Editar el archivo

Si no existe, créalo. Si existe, agrega la entrada `aac` dentro de `mcpServers`:

```json
{
  "mcpServers": {
    "aac": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer el-valor-de-MCP_AUTH_TOKEN-de-tu-.env"
      }
    }
  }
}
```

**Importante**: el token del header debe coincidir exactamente con `MCP_AUTH_TOKEN` en tu `.env`.

### Reiniciar Claude Desktop

Cerrar y abrir Claude Desktop completamente (no solo minimizar). En el menú debería aparecer un ícono de herramientas (🔌) indicando servers MCP conectados.

### Probar

En una conversación nueva:

> "Usa la herramienta revisar_publicacion para auditar esta publicación: 'Necesito arreglar el portón eléctrico del edificio. Es urgente.'"

Claude debería invocar la tool y devolver el análisis con alertas y citas.

---

## 3. Conectar a Claude Code

```bash
claude mcp add --transport http aac http://localhost:8000/mcp --header "Authorization: Bearer el-valor-de-MCP_AUTH_TOKEN-de-tu-.env"
```

Verificar que quedó registrado:

```bash
claude mcp list
```

Deberías ver `aac` en la lista.

---

## 4. Troubleshooting

### El server no levanta

- Verificar que el venv está activado: `which python` debe apuntar a `.venv/Scripts/python`.
- Verificar que `requirements.txt` está instalado: `pip list | grep mcp`.
- Ver logs detallados: `LOG_LEVEL=DEBUG python -m src.mcp_server.server`.

### Claude Desktop no muestra la tool

- Confirmar que el archivo `claude_desktop_config.json` es JSON válido (sin comas colgando).
- Reiniciar Claude Desktop (cerrar completamente, no solo minimizar).
- En Claude Desktop, ir a Settings → Developer → revisar si `aac` aparece listado.
- Si aparece con error rojo, click para ver el detalle (suele ser token incorrecto o server caído).

### Error 401 Unauthorized

- El token del header en `claude_desktop_config.json` no coincide con `MCP_AUTH_TOKEN` en `.env`.
- Verifica que copiaste el valor completo sin espacios ni comillas.

### Error "Connection refused"

- El server no está corriendo. Volver a levantarlo en otra terminal.
- Verificar que el puerto 8000 está libre: `netstat -an | findstr 8000` (Windows) o `lsof -i :8000` (Mac/Linux).

### Latencia alta (>5 segundos)

- Es la primera consulta después de iniciar: el modelo de embeddings se está cargando en memoria. Las siguientes serán más rápidas.
- Si sigue lento, revisar `LOG_LEVEL=DEBUG` para ver tiempos por etapa (retrieval vs LLM).

### El modelo alucina normativa

- El corpus normativo en `data/normativa/` puede estar incompleto.
- Verificar que el indexer corrió: `ls data/chroma/` debe tener archivos.
- Re-indexar: `python -m src.indexer.build_index`.

---

## 5. Modo alternativo: stdio (si streamable-http no funciona en tu cliente)

Algunos clientes antiguos de MCP solo soportan `stdio`. Para usar ese modo, el server tendría que exponer una entrada CLI sin HTTP. **No implementado en MVP** — el ejemplo del profesor tampoco lo usa. Si necesitas stdio, agregarlo como issue.
