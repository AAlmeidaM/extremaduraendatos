-- =============================================================================
--  extremadura-en-datos · Esquema inicial
--  Se aplica automaticamente al arrancar (ver src/extremadura_datos/db.py,
--  funcion ensure_schema). Escrito para poder ejecutarse repetidas veces sin
--  romper nada: todo IF NOT EXISTS / ON CONFLICT DO NOTHING.
-- =============================================================================

-- Fuentes de datos (INE, y en el futuro otras: Eurostat, Junta de Extremadura...)
CREATE TABLE IF NOT EXISTS fuente (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    url_base TEXT
);

-- Jerarquia territorial: pais -> ccaa -> provincia
CREATE TABLE IF NOT EXISTS territorio (
    id SERIAL PRIMARY KEY,
    nivel TEXT NOT NULL CHECK (nivel IN ('pais', 'ccaa', 'provincia')),
    codigo_ine TEXT,
    nombre TEXT NOT NULL,
    padre_id INTEGER REFERENCES territorio(id),
    UNIQUE (nivel, nombre)
);

-- Un "indicador" = una tabla concreta de una fuente (p.ej. tabla INE 50913,
-- el IPC por CCAA). Una tabla del INE casi siempre contiene MUCHAS series
-- (territorio x rubro x tipo de dato...), no una sola por territorio+periodo
-- — de ahi que haga falta el nivel `serie` de abajo.
CREATE TABLE IF NOT EXISTS indicador (
    id SERIAL PRIMARY KEY,
    fuente_id INTEGER NOT NULL REFERENCES fuente(id),
    tabla_id_externo TEXT NOT NULL,      -- id de tabla en la fuente (p.ej. "50913")
    codigo TEXT NOT NULL UNIQUE,          -- slug interno (p.ej. "ine_ipc_ccaa")
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,              -- 'precios' | 'turismo' | 'empleo' | ...
    -- 'pais' | 'ccaa' | 'provincia' | 'ccaa_y_provincia' (algunas tablas del
    -- INE traen ambos niveles mezclados en la misma respuesta)
    nivel_territorial TEXT NOT NULL
        CHECK (nivel_territorial IN ('pais', 'ccaa', 'provincia', 'ccaa_y_provincia')),
    periodicidad TEXT NOT NULL,           -- 'trimestral' | 'anual' | 'mensual'
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (fuente_id, tabla_id_externo)
);

-- Una "serie" = una combinacion concreta de dimensiones dentro de una tabla:
-- territorio + todo lo demas que la distinga (rubro, tipo de alojamiento,
-- sector de actividad, sexo...). El INE mete toda esa informacion en el
-- nombre de la serie (`Nombre`), asi que se guarda tal cual en
-- `nombre_origen`, y si el INE la da (casi siempre) tambien su propio
-- codigo de serie en `codigo_origen` (p.ej. "IPC256217").
--
-- ⚠️ IMPORTANTE (encontrado ejecutando esto contra datos reales, 2026-08-28,
-- tabla 2941 "Viajeros/pernoctaciones por tipo de alojamiento"): `nombre_origen`
-- NO es fiable como clave natural. Esa tabla trae dos series con `Nombre` Y
-- `MetaData` IDENTICOS ("Extremadura. Viajeros. Total.") pero `COD` y valores
-- distintos (EOT1715 vs EOT795) -- un duplicado real del propio INE. Usar
-- nombre_origen como clave (version anterior de este esquema) provoca
-- "ON CONFLICT DO UPDATE command cannot affect row a second time" al cargar
-- esta tabla (reproducido contra Postgres real). Por eso la clave natural es
-- `clave_natural` (columna generada = codigo_origen si lo hay, si no
-- nombre_origen) -- el COD de serie del INE es su propio identificador unico,
-- mucho mas fiable que el nombre.
--
-- `atributos` (JSONB): el resto de dimensiones de la serie tal y como las da
-- el array MetaData de la respuesta real del INE una vez quitado el
-- territorio -- p.ej. {"Tipo de dato": {"nombre": "Variacion mensual",
-- "codigo": "3"}, "Sexo": {...}}. Permite filtrar/agrupar por esas
-- dimensiones sin volver a parsear nombre_origen. Ver
-- src/extremadura_datos/parse.py.
CREATE TABLE IF NOT EXISTS serie (
    id BIGSERIAL PRIMARY KEY,
    indicador_id INTEGER NOT NULL REFERENCES indicador(id),
    territorio_id INTEGER NOT NULL REFERENCES territorio(id),
    codigo_origen TEXT,
    nombre_origen TEXT NOT NULL,
    atributos JSONB NOT NULL DEFAULT '{}'::jsonb,
    primera_vez_visto TIMESTAMPTZ NOT NULL DEFAULT now(),
    clave_natural TEXT GENERATED ALWAYS AS (COALESCE(codigo_origen, nombre_origen)) STORED,
    UNIQUE (indicador_id, clave_natural)
);

CREATE INDEX IF NOT EXISTS idx_serie_indicador  ON serie(indicador_id);
CREATE INDEX IF NOT EXISTS idx_serie_territorio ON serie(territorio_id);
CREATE INDEX IF NOT EXISTS idx_serie_atributos  ON serie USING GIN (atributos);

-- Si el esquema ya estaba aplicado de una version anterior (sin estas
-- columnas), esto las añade sin romper nada (idempotente). El ALTER de
-- clave_natural y su UNIQUE se hacen aparte porque ADD COLUMN no admite
-- GENERATED ALWAYS AS condicionalmente en una sola sentencia idempotente.
ALTER TABLE serie ADD COLUMN IF NOT EXISTS atributos JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'serie' AND column_name = 'clave_natural'
    ) THEN
        ALTER TABLE serie ADD COLUMN clave_natural TEXT
            GENERATED ALWAYS AS (COALESCE(codigo_origen, nombre_origen)) STORED;
        ALTER TABLE serie DROP CONSTRAINT IF EXISTS serie_indicador_id_nombre_origen_key;
        ALTER TABLE serie ADD CONSTRAINT serie_indicador_id_clave_natural_key
            UNIQUE (indicador_id, clave_natural);
    END IF;
END $$;

-- Tabla de hechos: un valor de una serie, en un periodo concreto
CREATE TABLE IF NOT EXISTS observacion (
    id BIGSERIAL PRIMARY KEY,
    serie_id BIGINT NOT NULL REFERENCES serie(id),
    periodo_fecha DATE NOT NULL,          -- fecha representativa del periodo (1er dia)
    anyo INTEGER NOT NULL,
    periodo_codigo TEXT,                  -- 'T1'..'T4', 'A' (anual), 'M01'..'M12'
    valor NUMERIC,
    unidad TEXT,
    escala TEXT,
    tipo_dato TEXT,
    secreto BOOLEAN NOT NULL DEFAULT FALSE,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (serie_id, periodo_fecha)
);

CREATE INDEX IF NOT EXISTS idx_observacion_serie   ON observacion(serie_id);
CREATE INDEX IF NOT EXISTS idx_observacion_periodo ON observacion(periodo_fecha);

-- Vista de consulta comoda: una fila = un valor, con todo el contexto ya
-- resuelto (fuente, indicador, territorio, serie). Pensada para consultar
-- directamente sin tener que repetir los JOIN cada vez.
CREATE OR REPLACE VIEW v_observacion AS
SELECT
    o.id,
    f.codigo            AS fuente,
    i.codigo            AS indicador,
    i.nombre            AS indicador_nombre,
    i.categoria,
    t.nivel             AS territorio_nivel,
    t.nombre            AS territorio,
    s.nombre_origen     AS serie,
    s.atributos         AS serie_atributos,
    o.periodo_fecha,
    o.anyo,
    o.periodo_codigo,
    o.valor,
    o.unidad,
    o.escala,
    o.tipo_dato,
    o.secreto
FROM observacion o
JOIN serie s      ON s.id = o.serie_id
JOIN indicador i  ON i.id = s.indicador_id
JOIN fuente f     ON f.id = i.fuente_id
JOIN territorio t ON t.id = s.territorio_id;

-- Registro de cada ejecucion de ingesta (para poder diagnosticar el cron diario)
CREATE TABLE IF NOT EXISTS carga_log (
    id BIGSERIAL PRIMARY KEY,
    indicador_id INTEGER REFERENCES indicador(id),
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en TIMESTAMPTZ,
    filas_leidas INTEGER,
    filas_insertadas INTEGER,
    filas_actualizadas INTEGER,
    estado TEXT NOT NULL CHECK (estado IN ('ok', 'error')),
    mensaje TEXT
);

-- --- Datos semilla -----------------------------------------------------------

INSERT INTO fuente (codigo, nombre, url_base) VALUES
    ('ine', 'Instituto Nacional de Estadistica', 'https://servicios.ine.es/wstempus/js')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    VALUES ('pais', '00', 'España', NULL)
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '11', 'Extremadura', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'provincia', '06', 'Badajoz', id FROM territorio
    WHERE nivel = 'ccaa' AND nombre = 'Extremadura'
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'provincia', '10', 'Cáceres', id FROM territorio
    WHERE nivel = 'ccaa' AND nombre = 'Extremadura'
ON CONFLICT (nivel, nombre) DO NOTHING;
