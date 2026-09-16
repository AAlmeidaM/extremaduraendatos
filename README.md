# Extremadura en Datos

Backend que descarga indicadores regionales/provinciales de distintas fuentes
públicas (INE y, desde 2026-09-15, Eurostat para la comparativa NUTS2 europea), los unifica en un esquema común y los guarda en PostgreSQL. Empieza
por el INE (economía y mercado laboral, Extremadura/Badajoz/Cáceres).

---

## Qué es

Un pipeline de ingesta (no expone API todavía — ver `PROJECT.md` §17 para el
motivo): scripts en Python que llaman a la API del INE, filtran las series de
Extremadura, y las cargan en una base de datos relacional pensada para poder
sumar más fuentes sin rehacer el esquema. Pensado para ejecutarse una vez al
día desde el Programador de tareas de Windows.

Para el detalle técnico completo: [PROJECT.md](PROJECT.md).
Para las tablas del INE usadas y por qué: [docs/fuentes-ine.md](docs/fuentes-ine.md).

---

## Requisitos

- Python 3.12 (ya instalado en este equipo)
- PostgreSQL 17 compartido en marcha (`E:\Lab\services\_shared`, ver
  `C:\OfficeLab\SERVICES.md`)

---

## Instalación

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Este script crea el entorno virtual, instala las dependencias, crea la base
de datos y el rol del proyecto (llamando a
`C:\OfficeLab\scripts\pg-new-database.ps1`), rellena `.env`, aplica el
esquema, inicializa Git y registra la tarea programada diaria. Ver el
detalle en [PROJECT.md §12](PROJECT.md#12-cómo-iniciar).

El catálogo completo (24 tablas, 23 activas) está verificado contra la API
real del INE y contra una carga real en producción (2026-08-28) — ver
`docs/fuentes-ine.md` y `PROJECT.md` §17 para el detalle. Si el INE cambia el
formato de alguna tabla en el futuro:

```powershell
.venv\Scripts\python -m extremadura_datos.inspect_table <id_tabla>
```

---

## Uso

```powershell
# Carga histórica completa (una sola vez, tras el setup)
.venv\Scripts\python -m extremadura_datos.ingest --modo historico

# Ingesta incremental (la que usa la tarea programada diaria)
.venv\Scripts\python -m extremadura_datos.ingest

# Solo un indicador
.venv\Scripts\python -m extremadura_datos.ingest --solo ine_ipc_ccaa

# Solo una fuente (ine | eurostat), p.ej. carga histórica de Eurostat NUTS2
.venv\Scripts\python -m extremadura_datos.ingest --modo historico --fuente eurostat

# Resumen de estructura y volumen de datos cargado
.venv\Scripts\python scripts\reporte_estructura.py
```

Para explorar los datos con un cliente gráfico: instalar
[DBeaver Community](https://dbeaver.io) (gratuito) y crear una conexión
PostgreSQL con los datos de `.env` (`DATABASE_URL`). La vista `v_observacion`
junta indicador + territorio + observación en una sola tabla.

---

## Configuración

Copiar `.env.example` a `.env` y rellenar los valores (lo hace
`scripts\setup.ps1` automáticamente):

```bash
cp .env.example .env
```

> ⚠️ **`.env` no se sube a Git.** Nunca escribas credenciales reales en
> `.env.example`, en el código ni en la documentación.

---

## Estructura

```
src\extremadura_datos\   Código fuente (paquete Python)
sql\                      Esquema de base de datos (001_schema.sql)
scripts\                  setup.ps1, run_ingesta.ps1, reporte_estructura.py,
                          verificar_carga.py
tests\                    Pruebas (sin red; usan un JSON de ejemplo)
docs\                     Documentación técnica adicional (fuentes-ine.md)
```

---

## Documentación

| Archivo | Contenido |
|---|---|
| [PROJECT.md](PROJECT.md) | Ficha técnica completa: arquitectura, datos, puertos, backup, recuperación |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |
| [docs/fuentes-europa-agro.md](docs/fuentes-europa-agro.md) | Fuentes verificadas de la ampliación: Eurostat, DG AGRI, FAO, embalses, lonjas |
| [docs/ampliacion-nuts2-agro.md](docs/ampliacion-nuts2-agro.md) | Plan y seguimiento de la ampliación NUTS2 europea + sector agropecuario (estado por fase, registro de avances) |
| [docs/fuentes-ine.md](docs/fuentes-ine.md) | Tablas del INE usadas, enlaces, y el aviso de que el parseo no se ha probado contra la API real |

Estándar del equipo: `C:\OfficeLab\PROJECT_STANDARD.md`
