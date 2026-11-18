"""Provision a field, laboratory or administrator login after organisation verification.
Example: python scripts/create_user.py --username officer01 --role government_officer \
  --display-name "A. Sharma" --organization "District Agriculture Office, Sehore"
The password is prompted securely and stored as a one-way hash.
"""
import argparse
import sys
from pathlib import Path
from getpass import getpass
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from werkzeug.security import generate_password_hash
from app.db import db_cursor

ROLES = {"government_officer", "company_officer", "lab_staff", "admin"}


def main():
    parser = argparse.ArgumentParser(description="Create an organisation or laboratory account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--organization", default="")
    args = parser.parse_args()
    password = getpass("Temporary password (minimum 12 characters): ")
    if len(password) < 12:
        parser.error("Password must contain at least 12 characters.")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        parser.error("Passwords do not match.")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT user_id FROM app_users WHERE username=%s", (args.username.strip(),))
        if cur.fetchone():
            parser.error("That username already exists.")
        cur.execute("""INSERT INTO app_users
            (username,password_hash,role,display_name,organization_name)
            VALUES (%s,%s,%s,%s,%s)""",
            (args.username.strip(), generate_password_hash(password), args.role,
             args.display_name.strip(), args.organization.strip() or None))
    print(f"Created {args.role} account for {args.display_name}. Share the temporary password privately.")


if __name__ == "__main__":
    main()
