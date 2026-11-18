from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_schema_has_all_expected_tables():
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    tables = set(re.findall(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)", sql, flags=re.I))
    assert tables == {
        "farms", "observations", "forecasts", "advisories",
        "virtual_farms", "virtual_farm_plots", "virtual_farm_assets", "soil_reports",
        "field_farmers", "field_visits", "soil_samples", "app_users",
    }


def test_virtual_farm_foreign_keys_and_boundary_fields_exist():
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "boundary_geojson LONGTEXT" in sql
    assert "fk_vfarm_plot" in sql
    assert "fk_vfarm_asset" in sql
    assert "UNIQUE KEY uq_virtual_farm_plot_code" in sql


def test_assisted_village_service_tables_have_traceability_fields():
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS field_farmers" in sql
    assert "CREATE TABLE IF NOT EXISTS field_visits" in sql
    assert "CREATE TABLE IF NOT EXISTS soil_samples" in sql
    assert "sample_code VARCHAR(48) NOT NULL UNIQUE" in sql
    assert "lab_verified TINYINT(1) NOT NULL DEFAULT 0" in sql
    assert "fk_soil_sample_farmer" in sql
    assert "farm_latitude DECIMAL(10,7)" in sql
    assert "farm_longitude DECIMAL(10,7)" in sql


def test_requirements_include_mysql_sha2_auth_support():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "PyMySQL[rsa]==1.1.2" in requirements
    assert "cryptography==50.0.2" in requirements


def test_sql_statement_splitter_preserves_semicolons_inside_quoted_strings():
    from scripts.init_db import split_sql_statements

    statements = split_sql_statements(
        "CREATE TABLE t (note VARCHAR(80) DEFAULT 'Prototype threshold; verify first');"
        "-- this comment ; must not split\nSELECT 1;"
    )
    assert len(statements) == 2
    assert "Prototype threshold; verify first" in statements[0]
    assert statements[1] == "SELECT 1"


def test_schema_is_split_into_complete_mysql_statements():
    from scripts.init_db import split_sql_statements

    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    assert len(statements) == 14  # CREATE DATABASE, USE, and twelve CREATE TABLE statements
    assert any("Prototype threshold, requires crop/soil-specific verification" in s for s in statements)
    assert all("CREATE TABLE IF NOT EXISTS" in s or s.startswith(("CREATE DATABASE", "USE ")) for s in statements)


def test_role_access_and_lab_assignment_columns_exist():
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "assigned_lab_organization VARCHAR(180) NULL" in sql
    assert "must_change_password TINYINT(1) NOT NULL DEFAULT 0" in sql
    assert "activation_code_hash VARCHAR(255) NULL" in sql
    assert "activation_expires_at DATETIME NULL" in sql
