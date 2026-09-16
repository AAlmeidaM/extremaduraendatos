# Fuente: INE — tablas usadas y por qué

**Última actualización:** 2026-08-28

API JSON del INE (Tempus3): <https://www.ine.es/dyngs/DAB/index.htm?cid=1100>
Base: `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/<id_tabla>`

El id de tabla es el mismo que aparece en la URL de visualización
`https://www.ine.es/jaxiT3/Tabla.htm?t=<id_tabla>` (el parámetro `t`).

## Modelo de datos: por qué existe la tabla `serie`

Cada tabla del INE casi nunca es "un valor por territorio y periodo": el IPC
(50913), por ejemplo, trae para Extremadura una serie por cada combinación de
rubro (general, alimentación, vivienda...) x tipo de dato (índice, variación
mensual, variación anual...) — decenas de series para el mismo territorio y
el mismo mes. Por eso el esquema tiene un nivel intermedio `serie` entre
`indicador` (la tabla) y `observacion` (un valor en un periodo): cada
combinación única de territorio + lo que distingue a la serie (guardado tal
cual en `serie.nombre_origen`) es una fila de `serie`, y `observacion`
cuelga de ahí. Ver `sql/001_schema.sql` y la vista `v_observacion` para
consultar todo ya unido.

## Tablas ingeridas (24)

### Precios

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_ipc_ccaa` | [50913](https://www.ine.es/jaxiT3/Tabla.htm?t=50913) | IPC Base 2021 | CCAA | Mensual |

### Industria y Empresa

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_soc_mercantiles_resumen_ccaa` | [13912](https://www.ine.es/jaxiT3/Tabla.htm?t=13912) | Resumen de sociedades mercantiles | CCAA | Mensual |
| `ine_soc_mercantiles_constituidas_ccaa` | [13913](https://www.ine.es/jaxiT3/Tabla.htm?t=13913) | Sociedades mercantiles constituidas | CCAA | Mensual |
| `ine_soc_mercantiles_disueltas_provincia` | [13923](https://www.ine.es/jaxiT3/Tabla.htm?t=13923) | Sociedades mercantiles disueltas | Provincia | Mensual |
| `ine_ipi_ccaa` | [26061](https://www.ine.es/jaxiT3/Tabla.htm?t=26061) | Índice de Producción Industrial (Base 2015) | CCAA | Mensual |
| `ine_icn_industria_ccaa` | [26002](https://www.ine.es/jaxiT3/Tabla.htm?t=26002) | Índices de cifras de negocios en la industria (Base 2015) | CCAA | Mensual |
| `ine_icn_comercio_menor_ccaa` | [25992](https://www.ine.es/jaxiT3/Tabla.htm?t=25992) | Índice de cifra de negocios comercio al por menor (Precios Constantes) | CCAA | Mensual |
| `ine_confianza_empresarial_ccaa` | [8027](https://www.ine.es/jaxiT3/Tabla.htm?t=8027) | Situación, expectativas e índice de confianza | CCAA | Trimestral |

### Turismo

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_turismo_viajeros_alojamiento_ccaa` | [2941](https://www.ine.es/jaxiT3/Tabla.htm?t=2941) | Viajeros, pernoctaciones por tipo de alojamiento | CCAA | Mensual |
| `ine_turismo_viajeros_pernoctaciones_ccaa` | [2074](https://www.ine.es/jaxiT3/Tabla.htm?t=2074) | Viajeros y pernoctaciones totales | CCAA | Mensual |
| `ine_turismo_establecimientos_ccaa` | [2942](https://www.ine.es/jaxiT3/Tabla.htm?t=2942) | Establecimientos, plazas y personal empleado por tipo de alojamiento | CCAA | Mensual |
| `ine_turismo_estancia_media_ccaa` | [2940](https://www.ine.es/jaxiT3/Tabla.htm?t=2940) | Estancia media, por tipo de alojamiento | CCAA | Mensual |
| `ine_turismo_gasto_turistas_ccaa` | [10839](https://www.ine.es/jaxiT3/Tabla.htm?t=10839) | Gasto de los turistas internacionales | CCAA | Mensual |

### Vivienda

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_hipotecas_provincia` | [3204](https://www.ine.es/jaxiT3/Tabla.htm?t=3204) | Hipotecas constituidas sobre fincas urbanas por entidad que concede el préstamo | Provincia | Mensual |
| `ine_compraventa_vivienda_ccaa_provincia` | [6150](https://www.ine.es/jaxiT3/Tabla.htm?t=6150) | Compraventa de viviendas según régimen y estado | CCAA y Provincia | Mensual |
| `ine_viviendas_transmitidas_ccaa_provincia` | [6149](https://www.ine.es/jaxiT3/Tabla.htm?t=6149) | Viviendas transmitidas según título de adquisición | CCAA y Provincia | Mensual |
| `ine_ipv_ccaa` | [25171](https://www.ine.es/jaxiT3/Tabla.htm?t=25171) | Índice de Precios de Vivienda (IPV). Base 2015 | CCAA | Trimestral |
| `ine_fincas_rusticas_ccaa_provincia` | [6147](https://www.ine.es/jaxiT3/Tabla.htm?t=6147) | Total fincas rústicas transmitidas según título de adquisición | CCAA y Provincia | Mensual |

### Empleo

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_coste_laboral_ccaa` | [6062](https://www.ine.es/jaxiT3/Tabla.htm?t=6062) | Coste laboral por hora efectiva, CCAA, sectores de actividad | CCAA | Trimestral |
| `ine_tiempo_trabajo_ccaa` | [6063](https://www.ine.es/jaxiT3/Tabla.htm?t=6063) | Tiempo de trabajo por trabajador y mes, CCAA, tipo de jornada, sectores de actividad | CCAA | Trimestral |
| `ine_epa_paro_provincia` | [3996](https://www.ine.es/jaxiT3/Tabla.htm?t=3996) | Tasas de actividad, paro y empleo por provincia y sexo (EPA) | Provincia | Trimestral |

### Demografía (población de referencia, 2026-09-16)

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_ecp_poblacion_ccaa_historico` | [56940](https://www.ine.es/jaxiT3/Tabla.htm?t=56940) | Población residente por fecha y sexo (ECP, definitivo desde 1971) — filtro `tv=356:15668` | CCAA + nacional | Trimestral |
| `ine_ecp_poblacion_ccaa` | [59238](https://www.ine.es/jaxiT3/Tabla.htm?t=59238) | Población residente por fecha y sexo (ECP, trimestres recientes provisionales) — `tv=356:15668` | CCAA + nacional | Trimestral |
| `ine_ecp_poblacion_provincia_historico` | [56945](https://www.ine.es/jaxiT3/Tabla.htm?t=56945) | Ídem por provincia — `tv=356:15668&tv=115:7&tv=115:11` (sin filtro de provincia el INE no la sirve) | Provincia | Trimestral |
| `ine_ecp_poblacion_provincia` | [59589](https://www.ine.es/jaxiT3/Tabla.htm?t=59589) | Ídem, trimestres recientes | Provincia | Trimestral |
| `ine_poblacion_ccaa` / `ine_poblacion_provincia` | 2853 / 2852 | Padrón (DPOP) — **inactivas: congeladas por el INE en 2021** | CCAA / Provincia | Anual |

### Mercado laboral y Economía (ya existían, no vienen del Excel)

| Código interno | Tabla INE | Nombre | Nivel | Periodicidad |
|---|---|---|---|---|
| `ine_epa_ccaa` | [75803](https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/75803) | Tasas de paro por grupos de edad, sexo y CCAA (EPA) | CCAA | Trimestral |
| `ine_cre_provincia` | [76926](https://www.ine.es/jaxi/Tabla.htm?tpx=76926) | PIB pm y VAB por ramas de actividad, precios corrientes, por provincia (CRE) | Provincia | Anual |
| `ine_cre_ccaa` | [77196](https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/77196) | PIB pm y VAB por ramas de actividad, precios corrientes, por CCAA (CRE) | CCAA | Anual |

> **Nota:** `ine_epa_paro_provincia` (tabla 3996, aportada por el usuario en
> el Excel) sustituye a la tabla 72989 que se había elegido de forma
> provisional en la primera versión de este proyecto para el mismo concepto
> (tasas de actividad/paro/empleo por provincia). Se adopta la 3996 por venir
> de la fuente curada por el usuario.
>
> **Corrección 2026-08-28:** `ine_cre_provincia` usaba el id `72946`, tomado
> del "identificador-api" de la ficha de datos.gob.es — pero ese número da
> 404 en `DATOS_TABLA` (no es un id real de tabla Tempus3, a diferencia de
> `75803` y `77196`, cuyos "identificador-api" sí coinciden con el id real).
> Se localizó el id correcto (`76926`) navegando la propia web del INE
> (Contabilidad regional de España → Resultados → Enfoque funcional →
> "provincias" → Tablas PC-Axis) y se verificó contra la API real.

Se filtran a Extremadura (CCAA) y Badajoz/Cáceres (provincias) — ver
`src/extremadura_datos/indicadores.py`. Las tablas "CCAA y Provincia" traen
ambos niveles en la misma respuesta y se filtran a los tres nombres a la vez.

## Verificado contra la API real (2026-08-28) — catálogo completo (24/24)

El JSON de `DATOS_TABLA` se ha descargado y examinado de verdad (vía
navegador, no solo documentación) para las **24 de 24** tablas del catálogo,
y se ha ejecutado `parsear_tabla()` (`src/extremadura_datos/parse.py`)
contra esas respuestas reales. Las 23 tablas activas (todas menos
`ine_turismo_gasto_turistas_ccaa`, ver más abajo por qué) se cargaron
además, todas juntas, dos veces seguidas, en un PostgreSQL 16 de prueba
limpio (esquema `sql/001_schema.sql` recién aplicado) usando el código real
(`db.get_or_create_indicador`, `db.upsert_observaciones`) — 382 filas de
`observacion` tras la primera pasada, 382 tras la segunda, mismos valores:
idempotencia confirmada (criterio de éxito de `PROJECT.md` §3) para el
catálogo completo, no solo para una muestra.

Primera tanda (7 tablas, elegidas por cubrir todas las combinaciones
estructurales conocidas):

| Tabla | Por qué se eligió | Resultado de la ejecución real |
|---|---|---|
| **50913** (IPC, CCAA) | Muchas series por territorio (rubro x tipo de dato) — el caso que motivó el modelo `serie` | 603 series en el fragmento, 31 de Extremadura, ninguna se pierde |
| **3996** (EPA paro, provincia) | Nivel `provincia` puro, trimestral | Badajoz y Cáceres correctos vía `MetaData` (`T3_Variable: "Provincias"`) |
| **6150** (Compraventa vivienda, CCAA y Provincia) | Nivel `ccaa_y_provincia` mezclado en la misma respuesta | 358 series, 15 de Extremadura/Badajoz/Cáceres con su nivel territorial correcto |
| **13912** (Sociedades mercantiles, CCAA) | Otra categoría (industria/empresa), para no asumir que solo IPC/EPA son representativos | 15 filas de Extremadura; confirma que `Valor: null` (dato no disponible) no rompe el parseo |
| **2941** (Turismo, viajeros/pernoctaciones, CCAA) | Otra categoría (turismo) | **Encontró un bug real** — ver más abajo |
| **77196** (CRE por CCAA, anual) | Periodicidad anual + **formato de respuesta distinto** (ver más abajo) | 42 filas de Extremadura |
| **76926** (CRE por provincia, anual) | Igual que 77196 pero a nivel provincia — y el id de tabla del catálogo original (72946) resultó ser incorrecto (ver más abajo) | 20 filas de Badajoz/Cáceres |

**Estructura real confirmada** (antes solo se tenía por documentación, y
tenía varios campos mal — ver CHANGELOG 2026-08-28):

- `Fecha` es un string ISO 8601 con offset (`"2025-12-01T00:00:00.000+01:00"`),
  no epoch en milisegundos.
- Unidad/escala/tipo de dato van en `T3_Unidad`, `T3_Escala`, `T3_TipoDato`
  (strings simples). `T3_Escala` suele venir en blanco (`" "`) — se trata como
  ausente.
- `MetaData` (lista de dimensiones con `T3_Variable`/`Nombre`/`Codigo`) es
  mucho más fiable que buscar el territorio como subcadena de `Nombre`, y es
  el método que usa `parse.py` ahora. Etiquetas territoriales confirmadas:
  `"Comunidades y Ciudades Autónomas"` (CCAA), `"Provincias"` (provincia),
  `"Total Nacional"` (nacional, se descarta siempre al filtrar). El resto de
  dimensiones (rubro, tipo de dato, sexo, régimen de vivienda...) varían por
  tabla y se guardan tal cual en `serie.atributos` (JSONB) — no hace falta
  conocerlas de antemano, `parse.py` las recoge todas menos la territorial.
- `T3_Periodo` (p.ej. `"M12"`, `"T4"`) se usa tal cual cuando está presente,
  en vez de derivarlo de la fecha.

**⚠️ Bug real encontrado y corregido — `nombre_origen` no es una clave
fiable (tabla 2941).** Esta tabla trae dos series con `Nombre` **y**
`MetaData` idénticos ("Extremadura. Viajeros. Total.") pero `COD` y valores
distintos (`EOT1715`=124471, `EOT795`=12134, mismo periodo). Con el esquema
anterior (clave = `nombre_origen`) esto rompía la carga de verdad contra
Postgres: `psycopg2.errors.CardinalityViolation: ON CONFLICT DO UPDATE
command cannot affect row a second time`. Solución: `serie.clave_natural`
(columna generada = `codigo_origen` si existe, si no `nombre_origen` — ver
`sql/001_schema.sql`) y la caché de `db.upsert_observaciones` usa la misma
lógica. El `COD` que da el INE es el identificador real de la serie; el
nombre es solo descriptivo. Repetida la carga contra Postgres tras el
arreglo: ambas series se conservan con su valor correcto y la segunda pasada
no duplica nada.

**⚠️ Segundo formato de respuesta encontrado (tablas 77196 y 76926, tipo
CRE).** Sin `COD`, sin `T3_Unidad`/`T3_Escala`/`T3_TipoDato`, y cada punto de
`Data` trae `NombrePeriodo` (`"2024(A)"`, `"2023(P)"`) en vez de
`Fecha`/`Anyo`/`T3_Periodo`. `parsear_tabla()` reconoce ambos formatos por
punto (ver `_fecha_desde_nombre_periodo()` en `parse.py`); la letra entre
paréntesis no es siempre "A" (varía por tabla) y se guarda tal cual en
`tipo_dato`.

**⚠️ Id de tabla incorrecto en el catálogo original — `ine_cre_provincia`.**
Tenía `72946` (tomado del "identificador-api" de la ficha de datos.gob.es),
que da 404 en `DATOS_TABLA`. Corregido a `76926` (ver nota en la tabla de
arriba). Esto sugiere que el "identificador-api" de datos.gob.es no siempre
coincide con el id real de tabla del INE — conviene verificar cualquier id
tomado de ahí en vez de asumirlo.

Segunda tanda (17 tablas restantes, verificación tabla por tabla hasta
completar el catálogo):

| Tabla | Resultado |
|---|---|
| **13913** (Soc. mercantiles constituidas, CCAA) | Correcta, sin hallazgos |
| **13923** (Soc. mercantiles disueltas, provincia) | Correcta, sin hallazgos |
| **26061** (IPI, CCAA) | Correcta; la respuesta es grande y hubo que pedir más texto para llegar a "Extremadura" en el orden alfabético — ver nota de método más abajo |
| **26002** (ICN industria, CCAA) | Correcta, sin hallazgos |
| **25992** (ICN comercio menor, CCAA) | Correcta; usa además la etiqueta `"Totales Territoriales"` para la fila "Total Nacional" (aparte de `"Comunidades y Ciudades Autónomas"` para las CCAA reales) — no afecta al filtrado, ver nota más abajo |
| **8027** (Confianza empresarial, CCAA) | Correcta, sin hallazgos |
| **2074** (Turismo, viajeros/pernoctaciones totales, CCAA) | Correcta, sin hallazgos |
| **2942** (Turismo, establecimientos, CCAA) | Correcta; una de las 15 series de Extremadura trae `"Data": []` (sin dato publicado para el periodo pedido) y por eso da 14 filas, no 15 — comportamiento esperado, no un bug |
| **2940** (Turismo, estancia media, CCAA) | Correcta, sin hallazgos |
| **10839** (Gasto turistas internacionales, CCAA) | **No desglosa Extremadura** — ver hallazgo más abajo, tabla desactivada |
| **3204** (Hipotecas, provincia) | Correcta, sin hallazgos |
| **6149** (Viviendas transmitidas, CCAA y provincia) | Correcta, sin hallazgos |
| **25171** (IPV, CCAA) | Correcta, sin hallazgos |
| **6147** (Fincas rústicas, CCAA y provincia) | Correcta, sin hallazgos |
| **6062** (Coste laboral, CCAA) | Correcta, sin hallazgos |
| **6063** (Tiempo de trabajo, CCAA) | Correcta; respuesta muy grande (1080 series), verificada filtrando con JavaScript en la propia página en vez de `get_page_text` — ver nota de método |
| **75803** (EPA tasas de paro, CCAA) | Correcta, sin hallazgos (21 series de Extremadura) |

**Confirmado, sin necesitar cambios en el código:** varias tablas de esta
segunda tanda usan para la fila "Total Nacional" una etiqueta de
`T3_Variable` distinta según la tabla (`"Totales Territoriales"` en 25992 y
2074, `"Total Nacional"` en 8027 y otras) — ninguna de las dos está en
`VARIABLES_TERRITORIALES`, así que esa fila nunca resuelve territorio por
`MetaData` y cae al respaldo por subcadena, que tampoco la encuentra (no
contiene "extremadura"/"badajoz"/"caceres") — se descarta correctamente. Las
filas de Extremadura de esas mismas tablas sí usan las etiquetas ya
soportadas (`"Comunidades y Ciudades Autónomas"`). Tampoco es un bug que una
serie traiga `"Data": []` (tabla 2942): esa combinación en concreto no tiene
valor publicado para el periodo pedido, así que no genera fila — correcto.

**⚠️ Hallazgo real (no un bug de parseo): la tabla 10839 no desglosa
Extremadura.** "Gasto de los turistas internacionales" (EGATUR) solo publica
por CCAA las seis con más turismo internacional (Andalucía, Baleares,
Canarias, Cataluña, Comunitat Valenciana, Madrid, confirmado listando las
CCAA presentes en `MetaData`); el resto, incluida Extremadura, va agregado
en "Otras Comunidades Autónomas" sin desglose propio. No hay id incorrecto
ni error de parseo que arreglar: el dato para Extremadura simplemente no
existe en esta tabla. `ine_turismo_gasto_turistas_ccaa` se marca
`activo=False` en `indicadores.py` para que `ingest.py` no la reintente cada
día en vano.

**Nota de método — filtrar con JavaScript en vez de `get_page_text` para
tablas grandes.** Para varias tablas de esta tanda, pedir el texto de la
página con `get_page_text` y un `max_chars` alto dio resultados
inconsistentes entre llamadas (probablemente por el árbol JSON colapsable
que renderiza Chrome) y en el peor caso (tabla 6063, 1080 series) truncó
antes de llegar a "Extremadura" en el orden alfabético incluso con
`max_chars` muy alto. La alternativa fiable: ejecutar
`JSON.parse(document.body.innerText)` dentro de la propia página
(`javascript_tool`) y filtrar ahí mismo por territorio antes de devolver el
resultado — pequeño, determinista, y evita depender de cuánto ha renderizado
el visor de JSON del navegador. Recomendado para cualquier tabla grande que
se añada en el futuro.

**Lo que sigue pendiente, aparte de esto:** confirmar el catálogo completo
también en el Postgres real del usuario (`officelab-postgres`), ya que todo
lo anterior se ha probado contra un PostgreSQL de prueba en el entorno
donde se ha ejecutado este trabajo — ver `PROJECT.md` §17. Para volver a
verificar una tabla concreta más adelante (por ejemplo si el INE cambia su
formato):

```bash
python -m extremadura_datos.inspect_table 50913
```

Esto descarga la tabla, la guarda en
`E:\Lab\datasets\extremadura-en-datos\raw\` y muestra por pantalla la primera
serie tal cual la devuelve el INE. Si hace falta ajustar algo, el sitio es
`parsear_tabla()`/`_extrae_territorio_y_atributos()` en `parse.py`.

## Tablas candidatas para más adelante

No incluidas todavía: demografía (población por provincia/CCAA, Padrón,
movimiento natural). El Excel del usuario no las incluye en este primer
bloque.

## Ampliar a otras fuentes

El esquema (`sql/001_schema.sql`) no es específico del INE: `fuente`,
`territorio`, `indicador`, `serie` y `observacion` son genéricos. Para añadir
una fuente nueva (Eurostat, Junta de Extremadura, SEPE...):

1. Insertar la fuente en la tabla `fuente`.
2. Escribir un cliente equivalente a `ine_client.py` para esa fuente.
3. Añadir sus indicadores a un catálogo (puede ser el mismo
   `indicadores.py` con un campo `fuente` o un módulo nuevo).
4. Reutilizar `db.upsert_observaciones` tal cual: solo necesita territorio,
   nombre de serie, fecha y valor — es agnóstico de dónde vino el dato.
