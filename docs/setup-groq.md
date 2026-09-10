# Groq API key — instrucciones para obtenerla

Groq ofrece un tier gratuito generoso para desarrollo. La key se obtiene en ~2 minutos.

## Pasos

1. Ir a https://console.groq.com
2. Click en "Sign in" (esquina superior derecha)
3. Login con cuenta Google (la más rápida)
4. Una vez dentro, ir a "API Keys" en el menú lateral izquierdo
5. Click en "Create API Key"
6. Darle un nombre (ej. "AAC-MVP")
7. **Copiar la key inmediatamente** — Groq no la muestra de nuevo por seguridad
8. Guardarla en un lugar seguro (1Password, Bitwarden, un archivo local cifrado)

## Pegar la key en el proyecto

Editar el archivo `.env` (créalo con `cp .env.example .env` si no existe):

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Sin comillas, sin espacios alrededor del `=`.

## Límites del tier gratuito

Los modelos disponibles en Groq cambian con el tiempo. Al momento de configurar este proyecto, los modelos con tier gratuito generoso incluyen:

- `openai/gpt-oss-120b` (modelo por defecto en el `.env.example`)
- `openai/gpt-oss-20b` (más rápido, menos preciso)
- `qwen/qwen3-32b`

Para nuestro MVP (auditor de publicaciones, ~1500 tokens por consulta), el límite diario de tier gratuito es **suficiente para desarrollo y demo**.

## Si te quedas sin cuota

- Si quieres cambiar el modelo por defecto, editar `.env`:
  ```
  GROQ_MODEL=openai/gpt-oss-20b
  ```
- Para ver qué modelos están disponibles ahora: desde una consola Python con `groq` instalado:
  ```python
  from groq import Groq
  client = Groq(api_key="tu-key")
  for m in client.models.list().data:
      print(m.id)
  ```

## Seguridad

- **Nunca** commitear el archivo `.env` al repositorio. Está en `.gitignore` por diseño.
- Si por error subes la key, **rota inmediatamente** en console.groq.com (botón "Revoke") y crea una nueva.
- La key del proyecto ejemplo (`mcp-asistente-curso_ejemplo`) no es la misma que la tuya — son cuentas separadas.

## Troubleshooting

**"Invalid API key"**: la key está mal copiada. Verifica que empieza con `gsk_` y que no hay espacios al inicio/final.

**"Rate limit exceeded"**: pasaste el límite. Espera unos minutos o cambia al modelo más chico.

**"Model not found"**: el modelo fue deprecado. Revisar modelos disponibles en https://console.groq.com/docs/models y actualizar `GROQ_MODEL` en `.env`.
