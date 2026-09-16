# web/ — extremaduraendatos.com

Sitio público del proyecto. Se publica en **Vercel** desde el repositorio de
GitHub con **Root Directory = `web`** (ver `docs/web-extremaduraendatos.md` §6).

- Estado actual: página provisional estática (`index.html`), sin build.
- `vercel.json` → `ignoreCommand`: Vercel solo reconstruye cuando cambia algo
  dentro de `web/` desde el último despliegue (`VERCEL_GIT_PREVIOUS_SHA`); si no
  hay despliegue previo, siempre construye. Corregido 2026-09-16: la primera
  versión comparaba solo `HEAD^` y canceló el primer despliegue porque el último
  commit no tocaba `web/`.
- Siguiente paso (§7 paso 2): sustituir la página provisional por el sitio en
  Astro con los datos exportados en `web/data/`.
