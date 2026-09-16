# Estado del proyecto y siguientes pasos

> **Documento de traspaso.** Resume en un solo sitio qué hay hecho, cómo se
> opera, qué se sabe que falla o limita, y qué queda por hacer, para poder
> retomar el proyecto más adelante (una persona o un agente de IA) sin
> reconstruir el contexto. El detalle vive en los documentos enlazados; aquí
> está el mapa.
>
> **Foto a:** 2026-09-16 · último commit al redactarlo: `2a149bc`
> (ver `git log`). Si retomas mucho después, empieza por §5 "Checklist para
> retomar".

---

## 1. Qué es y para qué

Backend de datos de **Extremadura en Datos**: descarga cada día indicadores
de fuentes públicas, los normaliza a un esquema común y los guarda en
PostgreSQL (`extremadura_en_datos` en `officelab-postgres`).

Objetivo final (decidido con el usuario):

1. Comparar **Extremadura con el resto de España** (INE, todas las CCAA).
2. Comparar **Extremadura con las regiones NUTS2 de la UE** (Eurostat).
3. Seguir el **sector agropecuario**: precios locales, europeos y mundiales.
4. Construir encima una **capa de análisis** (pandas → tabla `analisis_web`)
   y después una **web** que solo lea de esa capa (arquitectura de tres
   capas, `PROJECT.md` §4).

## 2. Qué hay hecho (a 2026-09-16)

### 2.1 Datos en producción

| Fuente | Módulo | Indicadores activos | Cobertura | Observaciones |
|---|---|---|---|---|
| INE (Tempus3) | `ine_client.py`, `parse.py`, `calendario.py` | 27 (+3 inactivos) | CCAA + España + Badajoz/Cáceres; histórico según tabla | ~1,16 M |
| INE – población trimestral (ECP) | ídem, con `ine_filtros` | 4 de los 27 | 1971 → 1-jul-2026 | 8.118 |
| Eurostat (NUTS2) | `eurostat_client.py`, `eurostat_parse.py`, `eurostat_ingest.py` | 9 | UE-27, 27 países, todas las NUTS2, Badajoz/Cáceres; 1980–2025 | 327.403 |
| Portal Agri-food (Comisión Europea) | `agrifood.py` | 7 | 27 países + media UE (+ mercados de Badajoz); 2010 → sep-2026 | 548.731 |
| FAO – índice de precios de los alimentos | `fao.py` | 1 | Mundo; 1990 → ago-2026 | 2.640 |
| Observatorio de Precios de la Junta | `observatorio_junta.py` | 1 (23 productos) | Badajoz/Cáceres; 2023 → sep-2026 | 1.246 |
| **Total** | | **48 en catálogo, 45 activos** | | **≈ 2.048.500** |

Indicadores inactivos (con motivo en `indicadores.py`):
`ine_turismo_gasto_turistas_ccaa` (el INE no desglosa Extremadura),
`ine_poblacion_ccaa` / `ine_poblacion_provincia` (Padrón congelado por el INE
en 2021; sus datos 1996–2021 se conservan).

### 2.2 Modelo de datos (resumen)

- Tablas: `fuente`, `territorio` (con `codigo_nuts`), `indicador`, `serie`
  (clave natural = código de serie de la fuente), `observacion`,
  `carga_log`, `calendario_publicacion`.
- Niveles de territorio: `pais`, `ccaa`, `provincia`, `nuts2` (regiones
  europeas no españolas), `agregado` (UE-27, Mundo). Las CCAA españolas son
  también las NUTS2 de Eurostat (mismo territorio).
- Periodicidades: anual (`A`), trimestral (`T1`), mensual (`M01`), semanal
  (`S07`, fecha = lunes, año ISO).
- Vistas: `v_observacion` (todo unido), `v_poblacion` (población por fuente
  y prioridad), **`mv_poblacion`** (materializada, población ya resuelta,
  se refresca al final de cada ingesta) y **`v_analisis`** (sin secreto
  estadístico, naturaleza del dato efectiva, `valor_por_1000_habitantes`
  para conteos con la población más reciente anterior al periodo).
- Todo el esquema está en `sql/001_schema.sql` y es idempotente: se reaplica
  en cada arranque de la ingesta.

### 2.3 Actualización diaria

Tarea programada `OfficeLab - extremadura-en-datos - ingesta diaria` (8:00)
→ `scripts/run_ingesta.ps1` → `python -m extremadura_datos.ingest`
(incremental). Cómo decide cada fuente si descarga:

| Fuente | Criterio incremental |
|---|---|
| INE | Calendario oficial de publicaciones (`calendario.py`); sin publicación pendiente no llama a la API |
| Eurostat | Consulta mínima del campo `updated`; si no cambió, no descarga; si cambió, últimos 6 años |
| Agri-food | Últimas 10 semanas (idempotente) |
| FAO | CSV completo (pocas KB) |
| Junta | Campaña actual, como mucho una vez cada 6 días (la web tarda ~45 s por producto) |

Al final siempre se refresca `mv_poblacion`. Log en
`E:\Lab\logs\extremadura-en-datos\latest.log` y por indicador en `carga_log`.

### 2.4 Hitos y correcciones importantes (orden cronológico)

- 26–28 ago: fase INE (24→26 tablas, todas las CCAA, calendario del INE,
  naturaleza del dato, `v_analisis`).
- 15 sep: plan de ampliación NUTS2 + agro (fase 0: verificación de fuentes).
- 15–16 sep: fase 1 Eurostat en producción.
- 16 sep: **la tarea diaria estaba rota desde el 28-ago** (PowerShell +
  stderr) → corregida; al ejecutarse de verdad salieron y se corrigieron 3
  fallos del calendario/parseo del INE; corregida la clasificación de
  variaciones en `v_analisis`.
- 16 sep: población → ECP trimestral; `mv_poblacion` (agregar `v_analisis`
  entera pasa de ~6,5 min a ~20 s).
- 16 sep: fase 3 precios agrarios en producción (Agri-food, FAO, Junta).

Detalle completo: `CHANGELOG.md`.

## 3. Cómo se opera

### 3.1 Comandos

```powershell
cd D:\Projects\extremadura-en-datos
.venv\Scripts\python -m extremadura_datos.ingest                          # incremental (lo que hace la tarea)
.venv\Scripts\python -m extremadura_datos.ingest --modo historico --solo ine_ipc_ccaa
.venv\Scripts\python -m extremadura_datos.ingest --modo historico --fuente eurostat   # ine|eurostat|agrifood|fao|junta_observatorio
.venv\Scripts\python -m pytest -q tests                                     # 28 tests sin red (pytest no está en requirements; instalar si hace falta)
```

### 3.2 Lanzadores `.bat` (doble clic, sin terminal)

Escriben su salida en `_ejecucion_claude\` (carpeta de trabajo excluida de
Git; los logs salen en codificación de consola cp850).

| Archivo | Qué hace | Salida |
|---|---|---|
| `probar_tarea_diaria.bat` | Ejecuta exactamente lo mismo que la tarea programada | `run_ingesta.txt`, `run_ingesta_estado.txt` |
| `carga_eurostat.bat` | Histórico de Eurostat + verificación | `eurostat.txt` |
| `carga_poblacion_ecp.bat` | Histórico de población ECP + verificación | `poblacion.txt` |
| `carga_precios.bat` | Histórico FAO + Agri-food + Junta (~25 min) | `precios.txt` |
| `carga_junta.bat` | Solo histórico de la Junta (~20 min) + verificación de precios | `junta.txt` |
| `verificar_naturaleza.bat` | Naturaleza del dato, población y normalización | `naturaleza.txt` |
| `verificar_precios.bat` | Resumen de precios agrarios | `verificar_precios.txt` |
| `reingesta_ccaa.bat`, `ejecutar_todo.bat`, `reporte_estructura.bat`, `exportar_analisis.bat`, `fetch_comparativa.bat` | Lanzadores de la fase INE (ver `PROJECT.md` §12 y CHANGELOG 28-ago) | varios |

### 3.3 Verificación rápida

- `scripts/verificar_carga.py`: filas por indicador y activos sin datos.
- `scripts/verificar_naturaleza.py`, `scripts/verificar_precios.py`.
- SQL útil:
  ```sql
  SELECT date(iniciado_en), estado, count(*) FROM carga_log GROUP BY 1,2 ORDER BY 1 DESC LIMIT 10;
  SELECT indicador, territorio, periodo_fecha, valor, valor_por_1000_habitantes
  FROM v_analisis WHERE territorio = 'Extremadura' AND indicador = 'eurostat_pib_nuts2' ORDER BY periodo_fecha DESC LIMIT 10;
  ```

### 3.4 Notas para trabajar con un agente de IA (Cowork)

- **Red:** solo el Python de Windows del PC llega a las APIs. Ni el entorno
  cloud ni la VM Linux de Cowork tienen salida a INE/Eurostat/etc. Para
  explorar APIs se usa el navegador integrado (JavaScript `fetch` en la
  propia página); los tests usan ficheros capturados.
- **Ejecutar en el PC:** la VM no puede lanzar programas de Windows. Se
  preparan `.bat` y se lanzan con doble clic mediante Computer Use en el
  Explorador (solo clic; coordenadas = 2× las de la captura a escala 0,5).
- **Git desde la VM:** `git status/commit` crean `.git/index.lock`; sin
  permiso de borrado en la carpeta se queda el bloqueo. Pedir antes permiso
  de borrado o hacer el commit desde Windows.
- **Pruebas de base de datos:** PostgreSQL 16 en el entorno cloud
  (`/usr/lib/postgresql/16/bin`), aplicando `sql/001_schema.sql` sobre el
  esquema anterior para simular producción.

## 4. Siguientes pasos (priorizados)

### 4.1 Pendientes cortos (antes o en paralelo a la fase 4)

1. **Confirmar que la tarea diaria corre sola.** Mañana (o el siguiente día
   laborable) revisar `E:\Lab\logs\extremadura-en-datos\latest.log` y
   `carga_log`: debe haber cargas con fecha del día y código de salida 0.
   Primera vez que se ejecuta tras todos los arreglos del 16-sep.
2. **Banco Mundial (Pink Sheet), último punto de la fase 3.** El fichero
   mensual es XLSX (`CMO-Historical-Data-Monthly.xlsx`, URL con identificador
   de publicación que cambia → buscar el enlace en
   `https://www.worldbank.org/en/research/commodity-markets`). Requiere
   añadir `openpyxl` a `requirements.txt`/`pyproject.toml` e instalarlo en
   el `.venv`. Seguir el patrón de `fao.py` (territorio `Mundo`, mensual).
   **Decisión pendiente del usuario:** instalar `openpyxl` o descartarlo.
3. **Reglas de plausibilidad de precios** (planificadas en fase 0): hoy solo
   se descartan precios vacíos o ≤ 0. Propuesta: por serie, marcar (no
   borrar) valores que se desvíen más de X % de la mediana de las 8 semanas
   previas; decidir si van a una tabla de revisión o a un flag en
   `observacion`.
4. **`!errorlevel!` en `carga_precios.bat`** imprime el literal (falta
   `setlocal enabledelayedexpansion`). Cosmético.
5. **Nombres de regiones europeas** en idioma original (Eurostat, p.ej.
   "Attiki"). Opcional: tabla de traducción si la web lo necesita.

### 4.2 Fase 4 — Capa de análisis (siguiente fase grande)

Estado: sin empezar. Diseño acordado solo a alto nivel (`PROJECT.md` §4 y
§17; `docs/ampliacion-nuts2-agro.md` §6 fase 4). **Antes de programar hay
que decidir con el usuario:**

| Decisión | Opciones / propuesta de partida |
|---|---|
| (a) Enganche al pipeline | Paso final de `ingest.py` (tras refrescar `mv_poblacion`) o script aparte llamado desde `run_ingesta.ps1` |
| (b) Alcance del análisis | Medias móviles y variaciones propias; rankings de CCAA y de NUTS2; Z-scores / Min-Max NUTS2 (con criterio de outliers); índices compuestos (pesos iguales, después PCA); correlación con desfase entre precios UE/mundo (Agri-food, FAO) y precios locales (Junta, mercados de Badajoz); relación población/empleo/VAB agrario |
| (c) Tabla de salida | Nombre y esquema de `analisis_web` (formato largo: indicador, territorio, periodo, métrica, valor…) |
| (d) Dependencias | `pandas` (y `numpy`, `scikit-learn` si PCA) en el `.venv` |

Restricciones conocidas para la fase 4:

- Trabajar por indicador/periodo, no sobre `v_analisis` entera (~20 s cada
  agregado completo).
- Población por habitante: `mv_poblacion` (ECP trimestral para España,
  Eurostat anual para Europa).
- Series del Observatorio de la Junta muy dispersas (semanas sueltas,
  temporadas): la correlación con desfase debe tolerar huecos o usar los
  mercados de Badajoz del portal Agri-food, más continuos.
- Las cotizaciones internacionales en tiempo real (MATIF/CBOT) están fuera
  por decisión (D3): el análisis de transmisión de precios usa precios
  europeos semanales y el índice FAO mensual.

### 4.3 Fases aplazadas

- **Fase 2 – embalses** (D8): fuente localizada (`BD-Embalses.zip` de
  MITECO, semanal por embalse desde 1988, probablemente Access `.mdb`).
  Al retomarla: descargar, ver el formato y elegir lector en Windows.
- **Lonjas en PDF/OCR** (D9, D10): descartadas por ahora. La Lonja de
  Extremadura requiere registro; la de Salamanca publica CSV abierto (solo
  últimas ~5 semanas) e histórico en PDF.
- **Fase 5 – web**: stack sin elegir; se construirá solo sobre la tabla de
  la fase 4.

## 5. Checklist para retomar

1. `officelab-postgres` en marcha (`cd E:\Lab\services\_shared ; docker compose up -d`).
2. Leer este documento, `PROJECT.md` §17 (entradas más recientes arriba) y
   las últimas entradas de `CHANGELOG.md`.
3. Comprobar que la tarea diaria sigue funcionando: `latest.log` y
   `SELECT date(iniciado_en), estado, count(*) FROM carga_log GROUP BY 1,2 ORDER BY 1 DESC LIMIT 10;`
4. Si falla: `probar_tarea_diaria.bat` y leer `_ejecucion_claude\run_ingesta.txt`.
5. `git log --oneline | head` para ver dónde se quedó el código; `pytest`
   para confirmar que los tests pasan.
6. Revisar la tabla "Estado por fase" de `docs/ampliacion-nuts2-agro.md` §6
   y elegir el siguiente punto de §4 de este documento.
7. **Al avanzar:** actualizar `docs/ampliacion-nuts2-agro.md` (§6 estado y
   §7 registro), `CHANGELOG.md`, `PROJECT.md` §17 y, si cambia la foto
   general, este documento.

## 6. Mapa de documentación

| Documento | Para qué |
|---|---|
| `README.md` | Entrada rápida: instalación y uso |
| `PROJECT.md` | Ficha técnica (estándar Office Lab), decisiones en §17 |
| `CHANGELOG.md` | Historial detallado de cambios |
| `docs/ESTADO-Y-SIGUIENTES-PASOS.md` | Este documento: foto actual y próximos pasos |
| `docs/ampliacion-nuts2-agro.md` | Plan de la ampliación NUTS2 + agro: decisiones D1–D10, estado por fase, registro de avances, riesgos |
| `docs/fuentes-europa-agro.md` | Fuentes verificadas de la ampliación (Eurostat, Agri-food, FAO, embalses, lonjas, Junta) y catálogos implementados (§7 Eurostat, §8 precios) |
| `docs/fuentes-ine.md` | Tablas del INE, verificación y demografía (ECP) |
