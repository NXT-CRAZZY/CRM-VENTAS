-- Extensiones usadas por la búsqueda (trigram + sin tildes) y base de datos de pruebas.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE DATABASE crm_test OWNER crm;
\connect crm_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
