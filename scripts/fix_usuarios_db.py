import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'database', 'Usuarios.db')
DB = os.path.abspath(DB)
print('DB path:', DB)

conn = sqlite3.connect(DB)
cursor = conn.cursor()

# Check columns
cursor.execute("PRAGMA table_info(usuarios)")
cols = [row[1] for row in cursor.fetchall()]
print('Existing columns:', cols)

if 'updated_at' not in cols:
    print('Adding updated_at column...')
    cursor.execute("ALTER TABLE usuarios ADD COLUMN updated_at TIMESTAMP")
    conn.commit()
    # Populate existing rows with current timestamp
    try:
        cursor.execute("UPDATE usuarios SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        conn.commit()
    except Exception as e:
        print('Could not populate updated_at:', e)
    print('updated_at column added and populated')
else:
    print('updated_at already present')

# Ensure trigger exists correctly: drop if exists, then create
try:
    cursor.execute("DROP TRIGGER IF EXISTS update_usuarios_timestamp")
    conn.commit()
    cursor.execute('''
        CREATE TRIGGER update_usuarios_timestamp
        AFTER UPDATE ON usuarios
        FOR EACH ROW
        BEGIN
            UPDATE usuarios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    ''')
    conn.commit()
    print('Trigger (re)created')
except Exception as e:
    print('Could not create trigger:', e)

conn.close()
print('Done')
