"""Create the MySQL database and tables from sql/schema.sql."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]


def split_sql_statements(sql: str) -> list[str]:
    """Split a MySQL script on statement delimiters, not semicolons in strings/comments."""
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i = 0
    length = len(sql)

    while i < length:
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < length else ""

        if quote is not None:
            current.append(char)
            if char == "\\" and quote in ("'", '"') and nxt:
                current.append(nxt)
                i += 2
                continue
            if char == quote:
                # SQL permits doubled quote characters inside quoted strings/identifiers.
                if nxt == quote:
                    current.append(nxt)
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        # Ignore SQL comments while scanning so comment semicolons cannot split statements.
        if char == "#":
            while i < length and sql[i] not in "\r\n":
                i += 1
            current.append("\n")
            continue
        if char == "-" and nxt == "-" and (i + 2 == length or sql[i + 2].isspace()):
            while i < length and sql[i] not in "\r\n":
                i += 1
            current.append("\n")
            continue
        if char == "/" and nxt == "*":
            end = sql.find("*/", i + 2)
            if end == -1:
                raise ValueError("Unterminated block comment in SQL script")
            current.append(" ")
            i = end + 2
            continue

        if char in ("'", '"', "`"):
            quote = char
            current.append(char)
            i += 1
            continue
        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    if quote is not None:
        raise ValueError(f"Unterminated {quote} quote in SQL script")
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def main() -> None:
    try:
        from dotenv import load_dotenv
        import pymysql
    except ImportError as exc:
        raise RuntimeError("Database setup requires python-dotenv and PyMySQL. Install requirements.txt.") from exc

    load_dotenv(ROOT / ".env")
    sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            for statement in split_sql_statements(sql):
                cur.execute(statement)
        print("MySQL database and tables are ready.")
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
