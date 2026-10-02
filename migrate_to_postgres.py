import sys
import os
import json
import sqlite3
import urllib.parse

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 migrate_to_postgres.py <POSTGRES_DATABASE_URL>")
        sys.exit(1)

    db_url = sys.argv[1].strip()
    print("==========================================================")
    print("🐘 FAST BATCH MIGRATION TO POSTGRESQL")
    print("==========================================================")

    import pg8000.native
    p = urllib.parse.urlparse(db_url)
    ssl_context = True if "sslmode=require" in db_url or p.hostname != "localhost" else False

    conn = pg8000.native.Connection(
        user=p.username,
        password=p.password,
        host=p.hostname,
        port=p.port or 5432,
        database=p.path.lstrip("/"),
        ssl_context=ssl_context
    )
    print("✅ Successfully connected to PostgreSQL!")

    # 1. Ensure tables
    conn.run("""
        CREATE TABLE IF NOT EXISTS whatsapp_session (
            id VARCHAR(255) PRIMARY KEY,
            data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.run("""
        CREATE TABLE IF NOT EXISTS processed_shipments (
            id SERIAL PRIMARY KEY,
            email_id VARCHAR(255) UNIQUE,
            subject TEXT,
            courier TEXT,
            tracking_number TEXT,
            pickup_code TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Batch upload WhatsApp session
    auth_dir = os.path.join(os.path.dirname(__file__), "whatsapp_bridge", "auth_info")
    if os.path.exists(auth_dir):
        files = [f for f in os.listdir(auth_dir) if f.endswith(".json")]
        print(f"Reading {len(files)} session files from disk...")
        
        items = []
        for fname in files:
            key_id = fname[:-5]
            fpath = os.path.join(auth_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                items.append((key_id, f.read()))

        BATCH_SIZE = 100
        print(f"Uploading {len(items)} keys in batches of {BATCH_SIZE}...")
        for i in range(0, len(items), BATCH_SIZE):
            chunk = items[i:i + BATCH_SIZE]
            # Construct multi-row VALUES query
            values_clauses = []
            params = {}
            for idx, (kid, val) in enumerate(chunk):
                values_clauses.append(f"(:k{idx}, :v{idx}, NOW())")
                params[f"k{idx}"] = kid
                params[f"v{idx}"] = val
            
            sql = f"""
                INSERT INTO whatsapp_session (id, data, updated_at)
                VALUES {', '.join(values_clauses)}
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
            """
            conn.run(sql, **params)
            print(f"  Processed {min(i + BATCH_SIZE, len(items))}/{len(items)} keys...")

        print("✅ All WhatsApp session files migrated!")

    # 3. Migrate SQLite shipments
    sqlite_path = os.path.join(os.path.dirname(__file__), "processed_emails.db")
    if os.path.exists(sqlite_path):
        with sqlite3.connect(sqlite_path) as sconn:
            cursor = sconn.cursor()
            cursor.execute("SELECT email_id, subject, courier, tracking_number, pickup_code FROM processed_shipments")
            rows = cursor.fetchall()
            print(f"Migrating {len(rows)} processed shipments...")
            for r in rows:
                conn.run("""
                    INSERT INTO processed_shipments (email_id, subject, courier, tracking_number, pickup_code, processed_at)
                    VALUES (:eid, :subj, :cour, :track, :pin, NOW())
                    ON CONFLICT (email_id) DO NOTHING
                """, eid=r[0], subj=r[1], cour=r[2], track=r[3], pin=r[4])
        print("✅ Shipments history migrated!")

    conn.close()

    # 4. Save to .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r") as f:
        env_lines = f.readlines()
    
    found = False
    new_lines = []
    for line in env_lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={db_url}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"\nDATABASE_URL={db_url}\n")
    
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    print("✅ DATABASE_URL saved to .env!")

if __name__ == "__main__":
    main()
