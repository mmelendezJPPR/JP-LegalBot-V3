import sqlite3
conn=sqlite3.connect('conversaciones.db')
conn.row_factory=sqlite3.Row
print('user_consent rows:')
for r in conn.execute("SELECT user_id, memory_consent, consent_at FROM user_consent"):
    print(dict(r))
print('\nlast 10 audit_log:')
for r in conn.execute("SELECT id, user_id, action, details, timestamp FROM audit_log ORDER BY id DESC LIMIT 10"):
    print(dict(r))
conn.close()
