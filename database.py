import os
import sqlite3
import urllib.parse
from datetime import datetime
from typing import Optional

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

def init_db():
    if DATABASE_URL:
        conn = _get_pg_conn()
        conn.run("""
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
        res = conn.run("SELECT 1 FROM processed_shipments WHERE email_id = :eid", eid=str(email_id))
        conn.close()
        return len(res) > 0
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
        conn.run("""
            INSERT INTO processed_shipments 
            (email_id, subject, courier, tracking_number, pickup_code, processed_at)
            VALUES (:eid, :subj, :cour, :track, :pin, NOW())
            ON CONFLICT (email_id) DO NOTHING
        """, eid=str(email_id), subj=subject, cour=courier, track=tracking_number, pin=pickup_code)
        conn.close()
    else:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO processed_shipments 
                (email_id, subject, courier, tracking_number, pickup_code, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(email_id), subject, courier, tracking_number, pickup_code, datetime.now()))
            conn.commit()
