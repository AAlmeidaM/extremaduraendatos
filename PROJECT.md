# PROJECT — Extremadura en Datos

> **Ficha técnica del proyecto.** Este archivo es la fuente de verdad del
> proyecto. Debe permitir que otra persona —o un agente de IA— retome el
> trabajo meses después sin ninguna explicación adicional.
>
> Estándar de referencia: `C:\OfficeLab\PROJECT_STANDARD.md`

**Última actualización:** 2026-08-28

---

## 1. Identificación

| Campo | Valor |
|---|---|
| **Nombre** | Extremadura en Datos |
| **Slug** | `extremadura-en-datos` |
| **Estado** | Production (datos reales cargados, 2026-08-28) |
| **Creado** | 2026-08-26 |
| **Responsable** | almei |

---

## 2. Descripción

Backend que descarga indicadores estadísticos regionales y provinciales de
distintas fuentes públicas (empezando por el INE), los normaliza a un
esquema común, y los almacena en PostgreSQL. No tiene interfaz ni API
todavía: por ahora es un pipeline de ingesta que se ejecuta una vez al día.

---

## 3. Objetivo

Tener, en una única base de datos relacional, series históricas comparables
de economía y mercado laboral para Extremadura, Badajoz y Cáceres,
actualizadas automáticamente, en vez de tener que consultarlas a mano en la
web del INE cada vez. Sirve de base para futuros análisis, cuadros de mando
o una API de consulta, que se añadirán en fases posteriores.

**Objetivo final del proyecto (aclarado por el usuario el 2026-08-28):** una
web de análisis, actualizada automáticamente cada día con el dato nuevo, en
la que el usuario comparte y explora cómo está Extremadura frente al resto
de España en estos indicadores. Esto implica una pieza que la fase 1 no
cubría: hace falta el dato de **todas las CCAA** (no solo Extremadura) más
el **total nacional**, para poder calcular esa comparativa sin depender de
consultas puntuales a la API en cada visita a la web. Ver la entrada del
2026-08-28 en §17 ("Ampliación a comparativa nacional") para el diseño y el
estado de esta ampliación.

**Criterio de éxito de esta fase:** ejecutar la ingesta y comprobar en
PostgreSQL que la tabla `observacion` tiene filas de los 24 indicadores
catalogados (ver `src\extremadura_datos\indicadores.py`) para
Extremadura/Badajoz/Cáceres, y que una segunda ejecución no duplica filas
(upsert correcto) ni pierde series (varias series por territorio y periodo
deben conservarse — ver §4). **Criterio de éxito de la ampliación nacional:**
los 19 indicadores de ámbito CCAA tienen, además, filas para las otras 18
CCAA/ciudades autónomas y para España (total nacional), con el mismo upsert
idempotente.

---

## 4. Arquitectura

```
Programador de tareas (diario) -> run_ingesta.ps1 -> python -m extremadura_datos.ingest
                                                            |
                                                            v
                                          IneClient (API JSON del INE, Tempus3)
                                                            |
                                                            v
                                    parse.py (filtra Extremadura/Badajoz/Cáceres,
                                               normaliza a filas por SERIE)
                                                            |
                                                            v
                                    PostgreSQL 17 compartido (base "extremadura_en_datos")
                                    fuente / territorio / indicador / serie / observacion / carga_log
```

Esquema pensado para admitir más fuentes sin cambiarlo, y para tablas con
muchas series por territorio (rubro, tipo de alojamiento, sector...): cada
tabla (`indicador`) tiene N series (`serie`, una por territorio +
combinación de dimensiones tal y como la nombra la fuente), y cada serie
tiene sus valores en el tiempo (`observacion`). Ver
`docs\fuentes-ine.md` §"Modelo de datos" y §"Ampliar a otras fuentes", y la
vista `v_observacion` para consultar todo ya unido en una sola fila.

---

## 5. Ubicaciones

| Qué | Ruta |
|---|---|
| **Código** | `D:\Projects\extremadura-en-datos` |
| **Base de datos** | Compartida: base `extremadura_en_datos` en `officelab-postgres` (no hay carpeta propia en `E:\Lab\databases`, ver §8) |
| **Logs** | `E:\Lab\logs\extremadura-en-datos` |
| **Datasets** | `E:\Lab\datasets\extremadura-en-datos\raw` (JSON crudo del INE, por trazabilidad) |
| **Backups** | `F:\Archive\Backups\extremadura-en-datos` |

---

## 6. Tecnologías

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| HTTP | requests | ≥2.31 |
| Base de datos | PostgreSQL (compartido) | 17 |
| Driver BD | psycopg2-binary | ≥2.9 |
| Config | python-dotenv | ≥1.0 |
| Programación de tareas | Programador de tareas de Windows | — |

---

## 7. Servicios

| Servicio | Función | ¿Propio del proyecto o compartido? |
|---|---|---|
| PostgreSQL 17 | Almacena las observaciones | Compartido (`infraestructura`, ver `C:\OfficeLab\SERVICES.md`) |
| Tarea programada `OfficeLab - extremadura-en-datos - ingesta diaria` | Ejecuta la ingesta cada día | Propio del proyecto |

Este proyecto no crea ningún servicio permanente (no hay contenedor Docker ni
servidor web propio) — solo una tarea programada, registrada en
`C:\OfficeLab\SERVICES.md`.

---

## 8. Docker

No usa Docker. Usa el PostgreSQL compartido (`officelab-postgres`), que ya
corre en Docker como infraestructura del Office Lab — este proyecto solo
tiene su base de datos y su rol dentro de esa instancia, creados con
`C:\OfficeLab\scripts\pg-new-database.ps1 -Slug extremadura-en-datos` (ver
`PROJECT_STANDARD.md` §2.1: motor compartido por defecto).

---

## 9. Puertos

No usa ningún puerto propio (no expone API ni servidor web en esta fase; se
conecta al puerto ya reservado 5432 de PostgreSQL compartido).

---

## 10. Variables de entorno

| Variable | Descripción | ¿Obligatoria? |
|---|---|---|
| `APP_ENV` | `development` / `testing` / `production` | No (default `development`) |
| `LOG_LEVEL` | Nivel de log | No (default `info`) |
| `LOG_DIR` | Carpeta de logs (`E:\Lab\logs\extremadura-en-datos`) | No |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL (rol/base propios del proyecto) | **Sí** |
| `DATASETS_DIR` | Carpeta donde se guarda el JSON crudo del INE | No |
| `INE_API_BASE` | URL base de la API del INE | No |
| `INE_REQUEST_TIMEOUT` | Timeout HTTP en segundos | No |
| `INE_REQUEST_DELAY_SECONDS` | Pausa entre peticiones al INE | No |

Plantilla: `.env.example`

---

## 11. Dependencias

**Internas**

- PostgreSQL 17 compartido (`officelab-postgres`), debe estar en marcha antes
  de ejecutar la ingesta.

**Externas**

- API JSON del INE (Tempus3): `https://servicios.ine.es/wstempus/js/ES` —
  servicio público gratuito, sin autenticación, sin SLA garantizado.

---

## 12. Cómo iniciar

Primera vez (crea entorno, base de datos, esquema, Git y tarea programada):

```powershell
cd D:\Projects\extremadura-en-datos
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Carga inicial (histórico completo, una sola vez tras el `setup.ps1`, para tener
series completas desde el principio y poder agregar por CCAA/provincia):

```powershell
.venv\Scripts\python -m extremadura_datos.ingest --modo historico
```

Ingesta manual incremental (fuera del horario de la tarea programada; solo
pide los últimos periodos, es la que usa la tarea diaria):

```powershell
.venv\Scripts\python -m extremadura_datos.ingest
```

Ambas admiten `--solo <codigo>` para un único indicador (ver
`indicadores.py`), p.ej. `--modo historico --solo ine_ipc_ccaa`.

Para ver un resumen legible de la estructura del esquema y del volumen de
datos cargado (totales, por territorio, por categoría, por periodicidad y
detalle por indicador):

```powershell
.venv\Scripts\python.exe scripts\reporte_estructura.py
```

Para explorar los datos libremente con un cliente gráfico (recomendado):
instalar [DBeaver Community](https://dbeaver.io) (gratuito) y crear una
conexión PostgreSQL con los datos de `.env` (`DATABASE_URL`: host, puerto,
base de datos, usuario y contraseña). La vista `v_observacion` ya trae
indicador + territorio + observación en una sola tabla, lista para
`SELECT * FROM v_observacion ...` sin tener que escribir los JOIN a mano.

Requisito previo: `officelab-postgres` en marcha
(`cd E:\Lab\services\_shared ; docker compose up -d`).

---

## 13. Cómo detener

No hay ningún proceso continuo que detener (la ingesta se ejecuta y termina).
Para desactivar la tarea programada diaria:

```powershell
Disable-ScheduledTask -TaskName 'OfficeLab - extremadura-en-datos - ingesta diaria'
```

---

## 14. Cómo actualizar

```powershell
cd D:\Projects\extremadura-en-datos
git pull            # si el repo tiene remoto
.venv\Scripts\pip install -e . --upgrade
.venv\Scripts\python -m extremadura_datos.bootstrap_db   # aplica cambios de esquema (idempotente)
```

Para añadir un indicador nuevo: editar
`src\extremadura_datos\indicadores.py` (no hace falta tocar el resto del
código, ver comentario al inicio de ese archivo).

---

## 15. Cómo hacer backup

```powershell
powershell -ExecutionPolicy Bypass -File C:\OfficeLab\scripts\pg-backup.ps1
```

Vuelca la base `extremadura_en_datos` (junto con las de los demás proyectos)
a `F:\Archive\Backups\databases\`. El código se protege con Git; el JSON
crudo de `E:\Lab\datasets\extremadura-en-datos\raw` es regenerable (no se
respalda, se puede volver a descargar del INE).

Destino: `F:\Archive\Backups\extremadura-en-datos\`

---

## 16. Cómo recuperar

1. Clonar/copiar el código a `D:\Projects\extremadura-en-datos`.
2. `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` (recrea venv,
   base de datos, rol, esquema y tarea programada).
3. Restaurar el volcado más reciente de `F:\Archive\Backups\databases\` con
   `pg_restore` (ver `C:\OfficeLab\BACKUP.md`).
4. Ejecutar `.venv\Scripts\python -m extremadura_datos.ingest` para traer lo
   que falte desde la última ingesta.

---

## 17. Observaciones relevantes

- **2026-08-28 — modelo de datos ampliado a nivel de serie, y catálogo
  ampliado a 24 tablas.** El usuario aportó `Datos_Extremadura_Mensual.xlsx`
  con 21 tablas del INE (Precios, Industria y Empresa, Turismo, Vivienda,
  Empleo). Varias de ellas (IPC, turismo, industria...) tienen múltiples
  series por territorio y periodo (por rubro, tipo de alojamiento, sector...),
  algo que el esquema original no soportaba sin perder datos (colisionaba en
  la restricción `UNIQUE(indicador_id, territorio_id, periodo_fecha)`). Se
  añadió la tabla `serie` entre `indicador` y `observacion` — ver §4 y
  `docs\fuentes-ine.md`. La tabla 72989 (EPA por provincia, elegida de forma
  provisional en la versión anterior) se sustituyó por la 3996 del Excel del
  usuario. Como el proyecto aún no se había desplegado (sin `.env`, sin base
  de datos creada), el cambio se hizo reescribiendo `sql/001_schema.sql`
  directamente, sin necesidad de una migración.
- **Sin API todavía, a propósito.** Fase 1 es solo ingesta + base de datos
  (decisión del 2026-08-26). Una API de consulta (FastAPI) sería un paso
  natural posterior, cuando haga falta consumir estos datos desde otro sitio.
- **Actualización diaria simplificada.** En vez de intentar seguir el
  calendario real de publicaciones del INE (distinto por tabla y a veces
  cambiante), la tarea corre todos los días y pide siempre los últimos
  periodos (`NULT_POR_DEFECTO` en `ingest.py`); como el upsert es idempotente,
  repetir no hace daño y no hace falta mantener lógica de calendario. Si en
  el futuro se prefiere minimizar peticiones al INE, se puede afinar por
  tabla usando el calendario de publicaciones real.
- **✅ Catálogo completo (24/24) verificado contra la API real y
  PostgreSQL real (2026-08-28).** `parsear_tabla()` se ha ejecutado contra
  JSON real de las 24 tablas del catálogo (no una muestra). Las 23 activas
  (todas menos `ine_turismo_gasto_turistas_ccaa`, ver abajo) se han cargado
  además juntas, dos veces seguidas, en un PostgreSQL 16 de prueba limpio
  con el código real (`db.py`): 382 filas de `observacion` en la primera
  pasada, 382 en la segunda, mismos valores — idempotencia confirmada
  (criterio de éxito de §3) para el catálogo completo. Esto obligó a
  corregir varios campos mal asumidos por documentación (`Fecha` ISO8601 no
  epoch-ms, `T3_Unidad`/`T3_Escala`/`T3_TipoDato`, territorio vía
  `MetaData`), y reveló varios problemas reales:
  - **`nombre_origen` no es clave fiable** (tabla 2941: dos series con
    nombre y MetaData idénticos pero COD y valores distintos rompían la
    carga). Arreglado con `serie.clave_natural` (COD si existe, si no el
    nombre) como clave real.
  - **Segundo formato de respuesta** (tablas CRE, 77196/76926): sin COD ni
    T3_Unidad/T3_Escala/T3_TipoDato, con `NombrePeriodo` en vez de Fecha.
    `parse.py` ya reconoce ambos formatos.
  - **Id de tabla incorrecto:** `ine_cre_provincia` tenía `72946` (404 real),
    corregido a `76926`.
  - **Tabla sin datos para Extremadura (no un bug):** `10839` (Gasto de
    turistas internacionales) solo desglosa por CCAA las seis con más
    turismo internacional; Extremadura va agregada en "Otras Comunidades
    Autónomas" sin desglose propio. Marcada `activo=False` en
    `indicadores.py` — no se reintenta cada día en vano.
  Detalle completo, tabla por tabla, en `docs\fuentes-ine.md`. Si el INE
  cambia el formato de alguna tabla en el futuro, usar `inspect_table.py`
  para volver a verificarla.
- **✅ Carga histórica real completada en producción (2026-08-28, con
  Computer Use).** Con permiso del usuario se activó el control remoto del
  PC y se ejecutó de verdad `scripts\setup.ps1` (creó `.env`, la base de
  datos `extremadura_en_datos` en `officelab-postgres`, aplicó el esquema y
  registró la tarea programada) y después
  `ingest.py --modo historico` para las 23 tablas activas. Resultado: **72.012
  observaciones reales** en la base de datos, ninguna tabla activa a 0 filas.
  En el camino se encontró y arregló un bug real y serio en
  `IneClient.fetch_tabla()` (bucle infinito: pedía "página siguiente" a la
  API del INE con un parámetro `page` que la API real no reconoce, así que
  nunca dejaba de pedir la misma respuesta completa una y otra vez) — ver
  CHANGELOG 2026-08-28 (5) para el detalle. Este era el primer uso real del
  cliente HTTP contra el INE en todo el proyecto: toda la verificación
  anterior (24/24 tablas) se había hecho con JSON capturado vía navegador,
  sin pasar nunca por `fetch_tabla()`. Ya no hay nada pendiente del usuario
  para tener el pipeline funcionando: falta solo revisar la tarea programada
  diaria dentro de un tiempo para confirmar que la ingesta incremental
  automática también funciona sin supervisión.
- **✅/⏳ Ampliación a comparativa nacional (2026-08-28, en curso).** El
  usuario aclaró el objetivo final: una web propia que compare Extremadura
  con el resto de España, actualizada a diario. Hasta ahora la base de datos
  solo guardaba Extremadura/Badajoz/Cáceres (el resto de CCAA se descartaba
  al filtrar); para poder comparar sin depender de una consulta en vivo a la
  API en cada visita (como se hizo puntualmente para el informe exploratorio
  de este mismo día), se ha ampliado:
  - `sql/001_schema.sql`: 18 filas nuevas en `territorio` (las CCAA y
    ciudades autónomas que faltaban, con su `codigo_ine` oficial), todas con
    `padre_id` = España. Sigue siendo idempotente (`ON CONFLICT (nivel,
    nombre) DO NOTHING`, mismo patrón que ya había).
  - `parse.py`: `VARIABLES_TERRITORIALES` reconoce ahora también
    `"Totales Territoriales"` / `"Total Nacional"` (las dos etiquetas que usa
    el INE para la fila-resumen nacional, según la tabla) como dimensión
    territorial — antes se descartaba sin guardar.
  - `db.py`: `TERRITORIO_CLAVE_A_NOMBRE` ampliado con las 18 CCAA nuevas más
    `"nacional"`/`"total nacional"` → territorio `España`.
  - `indicadores.py`: nuevas constantes `_TODAS_CCAA` /
    `_TODAS_CCAA_Y_PROVINCIA` (19 CCAA + Extremadura + las dos etiquetas
    nacionales, verificadas letra a letra contra JSON real de 7 tablas). Los
    **19 indicadores de ámbito CCAA** (16 `ccaa` + 3 `ccaa_y_provincia`,
    incluida la inactiva 10839) pasan a usarlas en vez de
    `_CCAA`/`_CCAA_Y_PROVINCIA`. **Los 4 indicadores exclusivamente
    provinciales** (`ine_cre_provincia`, `ine_epa_paro_provincia`,
    `ine_soc_mercantiles_disueltas_provincia`, `ine_hipotecas_provincia`)
    **no se han tocado** — decisión explícita del usuario, esas tablas del
    INE no traen desglose por CCAA que aprovechar.
  Validado primero en un PostgreSQL de prueba en el entorno cloud (tabla
  real 8027: 18 territorios distintos, upsert idempotente en 2 pasadas) y
  después **confirmado en producción**: se relanzó `ingest.py --modo
  historico` en el PC real (con Computer Use, `reingesta_ccaa.bat`) y
  terminó sin errores. Resultado real en `extremadura_en_datos`: de 72.012
  a **1.158.441 observaciones** (6.729 series, 22 territorios — los 19
  CCAA/ciudades autónomas + España + Badajoz + Cáceres), ningún indicador
  activo a 0 filas. España (fila nacional) sola aporta 71.332 observaciones,
  ya lista para comparar sin volver a pedirle nada a la API del INE.
- **Filtrado por nombre, no por código interno.** Se filtra Extremadura /
  Badajoz / Cáceres buscando esas palabras (sin acentos) en el nombre de
  serie que devuelve el INE, no por los códigos numéricos internos de
  variable/valor de Tempus3 (que no se pudieron consultar en este entorno).
  Es más lento que filtrar en la propia petición, pero no depende de
  adivinar esos códigos.
- **Alcance de indicadores.** 24 tablas catalogadas del INE (23 activas, ver
  arriba): Precios, Industria y Empresa, Turismo, Vivienda y Empleo (las 21
  del Excel del usuario, 2026-08-28) más Economía (PIB/VAB, tablas CRE) y
  Mercado laboral (EPA) de la fase anterior (2026-08-26). Demografía queda
  como siguiente candidato (ver `docs\fuentes-ine.md`).
- **Recomendación de verificación:** al ejecutar `inspect_table.py` por
  primera vez, empezar por `ine_ipc_ccaa` (tabla 50913) — es la que más
  series por territorio tiene y mejor ejercita el modelo `serie`. Si esa
  funciona, el resto (más simples) deberían funcionar igual.
