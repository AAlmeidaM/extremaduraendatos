# Extremadura en Datos

Backend que descarga indicadores regionales/provinciales de distintas fuentes
públicas, los unifica en un esquema común y los guarda en PostgreSQL. Empieza
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

**Antes de fiarte de la ingesta**, comprueba el JSON real del INE (ver el
aviso en [docs/fuentes-ine.md](docs/fuentes-ine.md)):

```powershell
.venv\Scripts\python -m extremadura_datos.inspect_table 75803
```

---

## Uso

```powershell
# Ingesta completa (los 4 indicadores)
.venv\Scripts\python -m extremadura_datos.ingest

# Solo uno
.venv\Scripts\python -m extremadura_datos.ingest --solo ine_epa_ccaa
```

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
scripts\                  setup.ps1, run_ingesta.ps1
tests\                    Pruebas (sin red; usan un JSON de ejemplo)
docs\                     Documentación técnica adicional (fuentes-ine.md)
```

---

## Documentación

| Archivo | Contenido |
|---|---|
| [PROJECT.md](PROJECT.md) | Ficha técnica completa: arquitectura, datos, puertos, backup, recuperación |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |
| [docs/fuentes-ine.md](docs/fuentes-ine.md) | Tablas del INE usadas, enlaces, y el aviso de que el parseo no se ha probado contra la API real |

Estándar del equipo: `C:\OfficeLab\PROJECT_STANDARD.md`
