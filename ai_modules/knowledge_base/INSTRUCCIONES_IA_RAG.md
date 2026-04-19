# Guía Técnica para Integración RAG (IA de Producción)

Este documento detalla la arquitectura de la base de conocimientos y la lógica de recuperación (Retrieval) implementada para optimizar el rendimiento y la precisión de los asistentes IA de la congregación.

## 1. Cambio de Arquitectura: De Monolítico a Jerárquico

Anteriormente, cada asistente cargaba un archivo JSON único. Esto generaba redundancia y saturación de contexto. La nueva arquitectura utiliza un **Índice Centralizado con Filtrado por Metadatos**.

### Ventajas:
- **Reducción de Latencia**: Búsquedas más rápidas en vectores específicos.
- **Zero-Hallucination en Códigos**: Procesamiento especial para el Manual de Cuentas.
- **Escalabilidad**: Soporte nativo para 8 establecimientos sin duplicidad de datos nacionales.

## 2. Esquema de Datos (Supabase / Vector DB)

Cada fragmento (chunk) en el archivo `base_conocimientos_supabase.json` sigue esta estructura de metadatos:

```json
{
  "texto_contenido": "[Nombre del Doc] Contenido...",
  "metadatos": {
    "fuente": "nombre_archivo.pdf",
    "nivel": "nacional | congregacional | institucional | rol",
    "establecimiento": "temuco | lota | etc",
    "rol": "utp | director | inspector | convivencia | representante"
  }
}
```

## 3. Lógica de Recuperación (Retrieval Strategy)

Para mantener la identidad de cada asistente, la IA debe aplicar filtros de metadatos en sus consultas vectoriales.

### Filtros por Rol (Ejemplo para Temuco):

| Asistente | Filtro de Metadatos Sugerido |
| :--- | :--- |
| **Representante** | `nivel IN ('nacional', 'congregacional') OR (establecimiento='temuco' AND nivel='institucional') OR (establecimiento='temuco' AND rol='representante')` |
| **UTP** | `nivel='nacional' OR (establecimiento='temuco' AND nivel='institucional') OR (establecimiento='temuco' AND rol='utp')` |
| **Director** | `nivel='nacional' OR (establecimiento='temuco' AND nivel='institucional') OR (establecimiento='temuco' AND rol='director')` |

## 4. Notas Especiales sobre el Manual de Cuentas

Se detectó que el Manual de Cuentas (11MB) causaba errores al ser fragmentado por caracteres fijos.
- **Solución**: Se utilizó un script especializado (`procesar_manual_cuentas.py`) que segmenta **por código de cuenta**.
- **Instrucción para la IA**: Al responder sobre cuentas contables, priorizar siempre los fragmentos con `nivel='congregacional'` y `fuente='Manual-de-cuentas'`. Estos fragmentos contienen la ruta completa de la cuenta para evitar confusiones.

## 5. Historial de Cambios y Solución de Errores

- **Problema**: Hallucinaciones en códigos de cuenta del Representante.
  - **Causa**: Fragmentación de tablas y ruido de documentos nacionales.
  - **Solución**: Aislamiento del manual y enriquecimiento de metadatos.
- **Problema**: Latencia y errores 500 en Railway.
  - **Causa**: Archivos JSON masivos cargados en memoria.
  - **Solución**: Migración a Supabase con persistencia vectorial y filtrado dinámico.

## 6. Resolución de Problemas (Troubleshooting)

- **La IA no encuentra un documento local**: Verificar que el filtro incluya `establecimiento='[nombre]'`.
- **La IA mezcla leyes de diferentes roles**: Asegurar que el filtro `rol` sea exclusivo del asistente actual.
- **Error en códigos contables**: Verificar que el chunk recuperado comience con el encabezado `CUENTA CONTABLE:`.

---
*Documento generado por Antigravity (Google Deepmind) para la optimización de la Intranet Congregacional.*
