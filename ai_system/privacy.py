import re
import sqlite3
import os
from datetime import datetime
from typing import Dict, Tuple

# Patrones básicos PII (ajustar según necesidad local)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(\+?\d{1,3}[\s-]?)?(?:\d{2,4}[\s-]?){2,4}\d{2,4}\b")
_ID_RE = re.compile(r"\b\d{6,15}\b")
_COORD_RE = re.compile(r"\b-?\d{1,3}\.\d+[, ]\s*-?\d{1,3}\.\d+\b")

DB_PATH = os.getenv('CONVERSACIONES_DB', 'conversaciones.db')

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def detect_pii(text: str) -> Dict[str, list]:
    return {
        'emails': _EMAIL_RE.findall(text),
        'phones': _PHONE_RE.findall(text),
        'ids': _ID_RE.findall(text),
        'coords': _COORD_RE.findall(text),
    }

def sanitize_text(text: str, redact_token='[REDACTED]') -> str:
    t = _EMAIL_RE.sub(redact_token, text)
    t = _PHONE_RE.sub(redact_token, t)
    t = _COORD_RE.sub(redact_token, t)
    t = _ID_RE.sub(redact_token, t)
    return t

def safe_to_send(text: str) -> Tuple[bool, Dict[str, list]]:
    hits = detect_pii(text)
    found = any(v for v in hits.values())
    return (not found, hits)

# --- DB helpers for consent and audit ---
def ensure_privacy_tables():
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_id_hash TEXT,
                action TEXT,
                resource_type TEXT,
                resource_id TEXT,
                success BOOLEAN,
                details TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_consent (
                user_id TEXT PRIMARY KEY,
                memory_consent INTEGER DEFAULT 0,
                consent_at DATETIME
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creando tablas de privacidad: {e}")

def log_audit(user_id: str, action: str, resource_type: str = None, resource_id: str = None, success: bool = True, details: str = None, ip_address: str = None):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # user_id_hash left null here; higher layers can provide hashed id if needed
        cur.execute('''
            INSERT INTO audit_log (user_id, user_id_hash, action, resource_type, resource_id, success, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, None, action, resource_type, resource_id, int(success), details, ip_address))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error registrando audit_log: {e}")

def set_user_consent(user_id: str, consent: bool):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute('''
            INSERT INTO user_consent (user_id, memory_consent, consent_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET memory_consent=excluded.memory_consent, consent_at=excluded.consent_at
        ''', (user_id, int(bool(consent)), now))
        conn.commit()
        conn.close()
        log_audit(user_id, 'consent_update', details=f'consent={consent}')
        return True
    except Exception as e:
        print(f"Error guardando consentimiento: {e}")
        return False

def get_user_consent(user_id: str) -> bool:
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute('SELECT memory_consent FROM user_consent WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return bool(row['memory_consent'])
        return False
    except Exception as e:
        print(f"Error leyendo consentimiento: {e}")
        return False

def export_user_data(user_id: str) -> dict:
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # Conversaciones
        cur.execute('SELECT id, pregunta, respuesta, timestamp FROM conversaciones WHERE usuario = ?', (user_id,))
        convs = [dict(r) for r in cur.fetchall()]
        # Aprendizajes (si existe tabla knowledge_facts)
        try:
            cur.execute('SELECT * FROM knowledge_facts WHERE author = ?', (user_id,))
            facts = [dict(r) for r in cur.fetchall()]
        except Exception:
            facts = []
        conn.close()
        log_audit(user_id, 'data_export', details=f'convs={len(convs)},facts={len(facts)}')
        return {'conversaciones': convs, 'learnings': facts}
    except Exception as e:
        print(f"Error exportando datos de usuario: {e}")
        return {'conversaciones': [], 'learnings': []}

def delete_user_data(user_id: str) -> dict:
    """Anonimizar o eliminar datos del usuario. Retorna conteo de filas afectadas."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # Contar y luego anonimizar conversaciones
        cur.execute('SELECT COUNT(*) as c FROM conversaciones WHERE usuario = ?', (user_id,))
        conv_count = cur.fetchone()['c']
        # Recomendamos anonimizar en vez de eliminar físico: reemplazar usuario y contenido
        cur.execute('''
            UPDATE conversaciones SET usuario = '[deleted]', pregunta = '[REDACTED]', respuesta = '[REDACTED]' WHERE usuario = ?
        ''', (user_id,))
        # También borrar aprendizajes si existe
        try:
            cur.execute('DELETE FROM knowledge_facts WHERE author = ?', (user_id,))
            facts_deleted = cur.rowcount
        except Exception:
            facts_deleted = 0
        conn.commit()
        conn.close()
        log_audit(user_id, 'data_delete', details=f'convs_anonimized={conv_count},facts_deleted={facts_deleted}')
        return {'conversaciones_anonimizadas': conv_count, 'learnings_deleted': facts_deleted}
    except Exception as e:
        print(f"Error eliminando datos de usuario: {e}")
        return {'conversaciones_anonimizadas': 0, 'learnings_deleted': 0}


def rectify_user_data(user_id: str, record_id: int, field: str, new_value: str) -> dict:
    """Allow a user to rectify a field in their own conversaciones record.
    Returns {'ok': True, 'changed': 1} on success or {'ok': False} if not allowed.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # Verify ownership
        cur.execute('SELECT usuario FROM conversaciones WHERE id = ?', (record_id,))
        row = cur.fetchone()
        if not row:
            return {'ok': False}
        if row['usuario'] != user_id:
            return {'ok': False}

        # Only allow editing of pregunta or respuesta for now
        if field not in ('pregunta', 'respuesta'):
            return {'ok': False}

        cur.execute(f'UPDATE conversaciones SET {field} = ? WHERE id = ?', (new_value, record_id))
        changed = cur.rowcount
        conn.commit()
        conn.close()
        log_audit(user_id, 'data_rectify', resource_type='conversaciones', resource_id=str(record_id), details=f'field={field}')
        return {'ok': True, 'changed': changed}
    except Exception as e:
        print(f"Error rectificando datos: {e}")
        return {'ok': False}


def apply_retention_policy(retention_days: int = 365) -> dict:
    """Simple retention job: anonymize conversations older than retention_days.
    Returns counts of affected rows.
    """
    try:
        import datetime
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM conversaciones WHERE datetime(timestamp) < ?', (cutoff.isoformat(),))
        to_anonymize = cur.fetchone()['c']
        cur.execute("UPDATE conversaciones SET usuario='[deleted]', pregunta='[REDACTED]', respuesta='[REDACTED]' WHERE datetime(timestamp) < ?", (cutoff.isoformat(),))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        # Log audit
        log_audit('[system]', 'retention_run', details=f'anonymized={affected}')
        return {'anonymized': affected, 'checked': to_anonymize}
    except Exception as e:
        print(f"Error aplicando retention policy: {e}")
        return {'anonymized': 0, 'checked': 0}
