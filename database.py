import os
import sqlite3
import urllib.parse
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_emails.db"))

def _get_pg_conn():
    import pg8000.native
    p = urllib.parse.urlparse(DATABASE_URL)
    ssl_context = True if "sslmode=require" in DATABASE_URL or p.hostname != "localhost" else False
    return pg8000.native.Connection(
        user=p.username,
        password=p.password,
        host=p.hostname,
        port=p.port or 5432,
        database=p.path.lstrip("/"),
        ssl_context=ssl_context
    )

def _escape_sql(val: Optional[str]) -> str:
    if val is None:
        return "NULL"
    return "'" + str(val).replace("'", "''") + "'"

def init_db():
    if DATABASE_URL:
        conn = _get_pg_conn()
        conn.execute_simple("""
            CREATE TABLE IF NOT EXISTS processed_shipments (
                id SERIAL PRIMARY KEY,
                email_id VARCHAR(255) UNIQUE,
                subject TEXT,
                courier TEXT,
                tracking_number TEXT,
                pickup_code TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.close()
    else:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_shipments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE,
                    subject TEXT,
                    courier TEXT,
                    tracking_number TEXT,
                    pickup_code TEXT,
                    processed_at TIMESTAMP
                )
            """)
            conn.commit()

def is_processed(email_id: str) -> bool:
    if DATABASE_URL:
        conn = _get_pg_conn()
        sql = f"SELECT 1 FROM processed_shipments WHERE email_id = {_escape_sql(str(email_id))}"
        ctx = conn.execute_simple(sql)
        conn.close()
        return len(ctx.rows) > 0 if ctx.rows else False
    else:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_shipments WHERE email_id = ?", (str(email_id),))
            return cursor.fetchone() is not None

def mark_processed(
    email_id: str,
    subject: str,
    courier: str,
    tracking_number: Optional[str] = None,
    pickup_code: Optional[str] = None
):
    if DATABASE_URL:
        conn = _get_pg_conn()
        sql = f"""
            INSERT INTO processed_shipments 
            (email_id, subject, courier, tracking_number, pickup_code, processed_at)
            VALUES (
                {_escape_sql(str(email_id))},
                {_escape_sql(subject)},
                {_escape_sql(courier)},
                {_escape_sql(tracking_number)},
                {_escape_sql(pickup_code)},
                NOW()
            )
            ON CONFLICT (email_id) DO NOTHING
        """
        conn.execute_simple(sql)
        conn.close()
    else:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO processed_shipments 
                (email_id, subject, courier, tracking_number, pickup_code, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(email_id), subject, courier, tracking_number, pickup_code, datetime.now()))
            conn.commit()
