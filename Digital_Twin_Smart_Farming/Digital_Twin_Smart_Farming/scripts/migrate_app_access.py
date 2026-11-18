"""Idempotent migration for role-based local accounts and organisation provenance."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db import connect

APP_USERS_DDL = """CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    display_name VARCHAR(160) NOT NULL,
    organization_name VARCHAR(180) NULL,
    farmer_id BIGINT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    must_change_password TINYINT(1) NOT NULL DEFAULT 0,
    activation_code_hash VARCHAR(255) NULL,
    activation_expires_at DATETIME NULL,
    last_login_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_user_farmer FOREIGN KEY (farmer_id) REFERENCES field_farmers(farmer_id) ON DELETE SET NULL,
    INDEX idx_app_user_role (role),
    INDEX idx_app_user_farmer (farmer_id)
) ENGINE=InnoDB"""

COLUMNS = {
    "field_farmers": {
        "registered_by_role": "VARCHAR(32) NULL",
        "registered_by_organization": "VARCHAR(180) NULL",
    },
    "field_visits": {
        "officer_role": "VARCHAR(32) NULL",
        "organization_name": "VARCHAR(180) NULL",
    },
    "soil_samples": {
        "collection_role": "VARCHAR(32) NULL",
        "collection_organization": "VARCHAR(180) NULL",
        "assigned_lab_organization": "VARCHAR(180) NULL",
        "lab_role": "VARCHAR(32) NULL",
        "lab_organization": "VARCHAR(180) NULL",
    },
    "app_users": {
        "must_change_password": "TINYINT(1) NOT NULL DEFAULT 0",
        "activation_code_hash": "VARCHAR(255) NULL",
        "activation_expires_at": "DATETIME NULL",
    },
}


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(APP_USERS_DDL)
            for table, columns in COLUMNS.items():
                for column, definition in columns.items():
                    cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
                    if not cur.fetchone():
                        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
                        print(f"Added {table}.{column}")
        conn.commit()
        print("Role-based account and organisation provenance migration is ready.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
