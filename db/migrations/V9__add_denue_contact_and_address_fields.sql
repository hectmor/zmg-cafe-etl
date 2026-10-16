-- Issue #66: confirmed against a real live DENUE load (4,125 elements) which
-- official fields INEGI actually returns with full/high coverage, beyond
-- what V7 already captured (ubicacion/areageo/clee). Same precedent as V7:
-- copied verbatim, no CHECK enum, always NULL for openstreetmap (Overpass
-- does not provide any of these).
ALTER TABLE staging.cafe_records
    ADD COLUMN estrato TEXT,
    ADD COLUMN tipo TEXT,
    ADD COLUMN tipo_vialidad TEXT,
    ADD COLUMN calle TEXT,
    ADD COLUMN num_exterior TEXT,
    ADD COLUMN colonia TEXT,
    ADD COLUMN cp TEXT,
    ADD COLUMN telefono TEXT,
    ADD COLUMN sitio_internet TEXT,
    ADD COLUMN correo_e TEXT;

COMMENT ON COLUMN staging.cafe_records.estrato IS
    'Official raw INEGI DENUE field `Estrato` (personnel range), copied '
    'verbatim. Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.tipo IS
    'Official raw INEGI DENUE field `Tipo` (Fijo/Semifijo), copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.tipo_vialidad IS
    'Official raw INEGI DENUE field `Tipo_vialidad`, copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.calle IS
    'Official raw INEGI DENUE field `Calle`, copied verbatim. Always NULL '
    'for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.num_exterior IS
    'Official raw INEGI DENUE field `Num_Exterior`, copied verbatim. Always '
    'NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.colonia IS
    'Official raw INEGI DENUE field `Colonia`, copied verbatim. Always NULL '
    'for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.cp IS
    'Official raw INEGI DENUE field `CP` (postal code), copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.telefono IS
    'Official raw INEGI DENUE field `Telefono`, copied verbatim (36% '
    'coverage in a real load). Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.sitio_internet IS
    'Official raw INEGI DENUE field `Sitio_internet`, copied verbatim (7% '
    'coverage in a real load). Always NULL for openstreetmap records.';
COMMENT ON COLUMN staging.cafe_records.correo_e IS
    'Official raw INEGI DENUE field `Correo_e`, copied verbatim (12.5% '
    'coverage in a real load). Always NULL for openstreetmap records.';

ALTER TABLE analytics.establecimientos
    ADD COLUMN estrato TEXT,
    ADD COLUMN tipo TEXT,
    ADD COLUMN tipo_vialidad TEXT,
    ADD COLUMN calle TEXT,
    ADD COLUMN num_exterior TEXT,
    ADD COLUMN colonia TEXT,
    ADD COLUMN cp TEXT,
    ADD COLUMN telefono TEXT,
    ADD COLUMN sitio_internet TEXT,
    ADD COLUMN correo_e TEXT;

COMMENT ON COLUMN analytics.establecimientos.estrato IS
    'Official raw INEGI DENUE field `Estrato` (personnel range), copied '
    'verbatim. Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.tipo IS
    'Official raw INEGI DENUE field `Tipo` (Fijo/Semifijo), copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.tipo_vialidad IS
    'Official raw INEGI DENUE field `Tipo_vialidad`, copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.calle IS
    'Official raw INEGI DENUE field `Calle`, copied verbatim. Always NULL '
    'for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.num_exterior IS
    'Official raw INEGI DENUE field `Num_Exterior`, copied verbatim. Always '
    'NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.colonia IS
    'Official raw INEGI DENUE field `Colonia`, copied verbatim. Always NULL '
    'for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.cp IS
    'Official raw INEGI DENUE field `CP` (postal code), copied verbatim. '
    'Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.telefono IS
    'Official raw INEGI DENUE field `Telefono`, copied verbatim (36% '
    'coverage in a real load). Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.sitio_internet IS
    'Official raw INEGI DENUE field `Sitio_internet`, copied verbatim (7% '
    'coverage in a real load). Always NULL for openstreetmap records.';
COMMENT ON COLUMN analytics.establecimientos.correo_e IS
    'Official raw INEGI DENUE field `Correo_e`, copied verbatim (12.5% '
    'coverage in a real load). Always NULL for openstreetmap records.';
