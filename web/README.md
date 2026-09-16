# web/ — extremaduraendatos.com

Sitio público del proyecto. Se publica en **Vercel** desde el repositorio de
GitHub con **Root Directory = `web`** (ver `docs/web-extremaduraendatos.md` §6).

- Estado actual: página provisional estática (`index.html`), sin build.
- `vercel.json` → `ignoreCommand`: Vercel solo reconstruye cuando cambia algo
  dentro de `web/` (los commits del backend no disparan despliegues).
- Siguiente paso (§7 paso 2): sustituir la página provisional por el sitio en
  Astro con los datos exportados en `web/data/`.
