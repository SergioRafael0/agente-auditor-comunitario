# Casos de prueba — publicaciones para testear el agente

Lista curada de publicaciones para probar el agente manualmente o en tests automatizados.
Están basadas en el caso "Proveedores & Comunidades" pero adaptadas al contexto chileno real.

---

## Caso 1 — Electricidad (esperado: alerta)

**Publicación:**
> "Necesito arreglar el portón eléctrico del edificio. A veces no abre. Es urgente."

**Categoría:** `electricidad`

**Esperado del agente:**
- Estado: `alerta`
- Alerta sobre técnico certificado SEC (electricista autorizado).
- Recomendación: pedir certificado SEC vigente al proveedor.

---

## Caso 2 — Ascensor (esperado: alerta)

**Publicación:**
> "El ascensor del edificio hace ruidos raros al subir. Necesito revisión."

**Categoría:** `ascensor`

**Esperado del agente:**
- Estado: `alerta`
- Alerta sobre mantenedor de ascensores certificado SEC.
- Cita a normativa SEC de ascensores (D.S. N°20/2015 o el vigente).
- Recomendación: exigir registro de mantenedor en SEC.

---

## Caso 3 — Mantención general (esperado: cumple)

**Publicación:**
> "Necesito pintar el interior del hall del edificio. Color blanco. Sin urgencia."

**Categoría:** `general`

**Esperado del agente:**
- Estado: `cumple`
- Sin alertas regulatorias críticas.
- Eventual mención a Ley 21.442 sobre gastos comunes si la pintura es cargo del comité.

---

## Caso 4 — Sin categoría clara (esperado: no_cumple)

**Publicación:**
> "Necesito ayuda con unas cosas del edificio."

**Categoría:** `general` (forzada porque no se especifica)

**Esperado del agente:**
- Estado: `no_cumple`
- Alerta sobre falta de detalle en la publicación.
- Recomendación: especificar categoría, descripción y urgencia.

---

## Caso 5 — Gas (esperado: alerta)

**Publicación:**
> "La caldera a gas del edificio no calienta bien. Necesito técnico."

**Categoría:** `gas`

**Esperado del agente:**
- Estado: `alerta`
- Alerta sobre técnico gasista autorizado SEC.
- Recomendación: exigir certificación SEC vigente y comprobante de revisión periódica.

---

## Caso 6 — Agua / sanitarias (esperado: cumple con recomendación)

**Publicación:**
> "Hay una filtración en el baño del primer piso. Necesito un gasfíter."

**Categoría:** `agua`

**Esperado del agente:**
- Estado: `cumple` o `alerta` (depende de la normativa indexada).
- Si hay recomendación de Ley 21.442 sobre aviso al comité, incluirla.

---

## Caso 7 — Trabajo en altura (esperado: alerta)

**Publicación:**
> "Necesito limpiar las canaletas del techo del edificio de 8 pisos."

**Categoría:** `general` (o nueva `altura`)

**Esperado del agente:**
- Estado: `alerta`
- Alerta sobre normativa de trabajo en altura (si está indexada) o al menos recomendación de seguridad.

---

## Caso 8 — Publicación bien hecha (esperado: cumple)

**Publicación:**
> "Necesito cambio de ampolletas en áreas comunes. El edificio cuenta con instalación eléctrica al día. Solicitamos proveedor con experiencia comprobable en edificios. Plazo: 2 semanas."

**Categoría:** `electricidad`

**Esperado del agente:**
- Estado: `cumple`
- Eventual recordatorio: "aunque no se requiere certificación SEC para cambio simple de ampolletas, se recomienda que el proveedor acredite experiencia".

---

## Uso en tests automatizados

Estos casos están en `tests/test_auditor.py` y se usan como fixtures para validar que el agente devuelve alertas razonables. Los tests **mockean Groq** con respuestas pregrabadas para no gastar tokens en CI.

Para probar manualmente el agente con estos casos:

```bash
python -m src.agent.auditor \
  --texto "Necesito arreglar el portón eléctrico del edificio. A veces no abre. Es urgente." \
  --categoria electricidad
```
