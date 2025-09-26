#!/usr/bin/env python3
"""
Inicializa la base de datos hybrid_knowledge.db a partir de database/init_db.sql
"""
import sqlite3
from pathlib import Path

SQL_PATH = Path('database') / 'init_db.sql'
DB_PATH = Path('database') / 'hybrid_knowledge.db'


def apply_sql(sql_path: Path, db_path: Path):
    if not sql_path.exists():
        print(f"❌ Archivo SQL no encontrado: {sql_path}")
        return False
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.executescript(sql)
        conn.commit()
        conn.close()
        print(f"✅ SQL aplicado correctamente en: {db_path}")
        return True
    except Exception as e:
        print(f"❌ Error aplicando SQL: {e}")
        return False


if __name__ == '__main__':
    DB_PATH.parent.mkdir(exist_ok=True)
    print(f"🔧 Inicializando base de datos híbrida en: {DB_PATH}")
    ok = apply_sql(SQL_PATH, DB_PATH)
    if ok:
        print("✅ hybrid_knowledge.db inicializada correctamente")
    else:
        print("❌ Error inicializando hybrid_knowledge.db")
