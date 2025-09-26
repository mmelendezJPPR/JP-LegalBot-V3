"""ai_system.learn

Funciones mínimas para almacenar "aprendizajes" derivados de interacciones.

Este módulo ofrece utilidades ligeras y seguras para:
- Normalizar consultas
- Guardar un `knowledge_fact` y una entrada en `faqs` cuando un planificador
  solicita explícitamente que el sistema "aprenda" algo de la interacción.
- Recuperar los últimos aprendizajes.

Diseño: mantenerlo pequeño y robusto. Si la base de datos no está disponible,
las funciones fallan silenciosamente y registran el error (no interrumpen el flujo).
"""
from typing import List, Dict, Optional
import uuid
import json
import logging

from .db import get_conn, insert_knowledge_fact, upsert_faq
from .config import DB_PATH

logger = logging.getLogger(__name__)


def _normalize_query(q: str) -> str:
    if not q:
        return ''
    return ' '.join(q.lower().strip().split())


def save_learning(conversation_id: str, user_query: str, assistant_response: str,
                  citations: Optional[List[str]] = None, fact_type: str = 'faq', tags: Optional[Dict] = None) -> Optional[str]:
    """Guardar un aprendizaje mínimo en la base `knowledge_facts` y una FAQ.

    - conversation_id: id de la conversación (para trazabilidad)
    - user_query: la pregunta o instrucción del usuario (se normaliza para FAQ)
    - assistant_response: contenido a almacenar como hecho/respuesta
    - citations: lista opcional de citas/metadatos
    - fact_type: tipo a guardar en knowledge_facts (por ejemplo 'faq' o 'definicion')
    - tags: diccionario opcional que se serializa a JSON

    Retorna el id del fact guardado o None en caso de fallo.
    """
    try:
        fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        faq_id = f"faq_{uuid.uuid4().hex[:12]}"

        citation = (citations[0] if citations and len(citations) > 0 else f"conversation:{conversation_id}")
        tags = tags or {}
        # Añadir metadatos básicos
        tags.update({'conversation_id': conversation_id, 'source': 'conversation'})

        # Limitar longitud para evitar blowup
        max_content = 4000
        content = (assistant_response or '')[:max_content]

        # Insertar en DB usando el context manager; soportar múltiples esquemas
        with get_conn(DB_PATH) as con:
            try:
                # Detectar columnas de la tabla knowledge_facts
                cur = con.execute("PRAGMA table_info(knowledge_facts)")
                cols = [r[1] for r in cur.fetchall()]
            except Exception:
                cols = []

            try:
                if 'content' in cols and 'tags' in cols:
                    # Usar helper que asume columnas content, tags
                    try:
                        insert_knowledge_fact(con, fact_id, content, citation, fact_type, tags=tags)
                    except Exception as e:
                        logger.warning(f"⚠️ insert_knowledge_fact falló: {e}")
                elif 'fact_text' in cols:
                    # Esquema legacy: id es INTEGER AUTOINCREMENT y fact_text almacena el contenido
                    try:
                        cur = con.execute(
                            "INSERT INTO knowledge_facts(fact_text, citation, confidence, usage_count) VALUES (?, ?, ?, ?)",
                            (content, citation, None, 0)
                        )
                        # Obtener rowid generado y construir un id legible
                        rowid = cur.lastrowid if hasattr(cur, 'lastrowid') else None
                        if not rowid:
                            # intentar obtener last_insert_rowid()
                            try:
                                rowid = con.execute('SELECT last_insert_rowid()').fetchone()[0]
                            except Exception:
                                rowid = None
                        if rowid:
                            fact_id = f"fact_{int(rowid)}"
                    except Exception as e:
                        logger.warning(f"⚠️ Inserción legacy en knowledge_facts falló: {e}")
                else:
                    # Intentar una inserción genérica (columna content)
                    try:
                        con.execute(
                            "INSERT OR REPLACE INTO knowledge_facts(id, content, citation, type, tags) VALUES (?, ?, ?, ?, ?)",
                            (fact_id, content, citation, fact_type, json.dumps(tags))
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Inserción fallback en knowledge_facts falló: {e}")

            except Exception as e:
                logger.warning(f"⚠️ Error insertando fact: {e}")

            # Crear o actualizar FAQ asociado a la consulta normalizada
            try:
                query_norm = _normalize_query(user_query)
                citations_json = citations or []
                # upsert_faq debería funcionar con el esquema actual de `faqs`.
                upsert_faq(con, faq_id, query_norm, content, citations_json)
            except Exception as e:
                logger.warning(f"⚠️ No se pudo upsert FAQ: {e}")

        logger.info(f"✅ Aprendizaje procesado: {fact_id} (faq: {faq_id})")
        return fact_id

    except Exception as e:
        logger.error(f"❌ Error save_learning: {e}")
        return None


def list_recent_learnings(limit: int = 20) -> List[Dict]:
    """Devolver una lista simple de los aprendizajes más recientes.

    Cada item: {id, content, citation, type, tags, created_at}
    """
    try:
        with get_conn(DB_PATH) as con:
            # Detectar columnas
            cur = con.execute("PRAGMA table_info(knowledge_facts)")
            cols = [r[1] for r in cur.fetchall()]

            out = []
            if 'content' in cols:
                sel = con.execute("SELECT id, content AS content, citation, type, tags, created_at FROM knowledge_facts ORDER BY created_at DESC LIMIT ?", (limit,))
                rows = sel.fetchall()
                for r in rows:
                    try:
                        tags = json.loads(r['tags']) if r['tags'] else {}
                    except Exception:
                        tags = {}
                    out.append({
                        'id': r['id'],
                        'content': r['content'],
                        'citation': r['citation'],
                        'type': r.get('type'),
                        'tags': tags,
                        'created_at': r['created_at']
                    })

            elif 'fact_text' in cols:
                sel = con.execute("SELECT id, fact_text AS content, citation, created_at FROM knowledge_facts ORDER BY created_at DESC LIMIT ?", (limit,))
                rows = sel.fetchall()
                for r in rows:
                    out.append({
                        'id': r['id'],
                        'content': r['content'],
                        'citation': r['citation'],
                        'type': None,
                        'tags': {},
                        'created_at': r['created_at']
                    })

            else:
                # Fallback genérico
                sel = con.execute("SELECT id, rowid, created_at FROM knowledge_facts ORDER BY created_at DESC LIMIT ?", (limit,))
                rows = sel.fetchall()
                for r in rows:
                    out.append({'id': r[0], 'content': None, 'citation': None, 'type': None, 'tags': {}, 'created_at': r[2] if len(r) > 2 else None})

            return out
    except Exception as e:
        logger.warning(f"⚠️ list_recent_learnings falló: {e}")
        return []


def summarize_learnings(limit: int = 10) -> str:
    """Resumen corto legible de los últimos aprendizajes para mostrar al usuario."""
    items = list_recent_learnings(limit)
    if not items:
        return "No he almacenado aprendizajes todavía. Pide explícitamente que guarde una respuesta con 'APRENDER: <tu texto>' o 'por favor aprende...'."

    parts = []
    for it in items[:limit]:
        snippet = it['content'][:300].replace('\n', ' ')
        parts.append(f"- [{it['id']}] {snippet} ({it['created_at']})")
    return "\n".join(parts)


def ingest_conversations(source_db_path: Optional[str] = None, limit: Optional[int] = None) -> Dict:
    """Ingesta segura desde la base `conversaciones.db` hacia la base de conocimiento.

    - source_db_path: ruta del archivo SQLite de conversaciones (por defecto busca 'database/conversaciones.db' o './conversaciones.db')
    - limit: máximo número de filas a procesar en una ejecución (None = ilimitado)

    Retorna un resumen: {'processed': n, 'errors': m, 'last_processed_source_id': id}
    """
    import sqlite3
    from pathlib import Path
    from datetime import datetime

    try:
        # Determinar ruta de origen: preferir './conversaciones.db' si existe
        p_root = Path('conversaciones.db')
        p_default = Path('database') / 'conversaciones.db'
        source = Path(source_db_path) if source_db_path else (p_root if p_root.exists() else p_default)
        if not source.exists():
            return {'processed': 0, 'errors': 1, 'message': f'Source DB not found: {source}'}

        # Conectar DB de origen y target
        src_conn = sqlite3.connect(str(source))
        src_conn.row_factory = sqlite3.Row
        src_cur = src_conn.cursor()

        # Target (hybrid knowledge DB)
        tgt_path = Path(DB_PATH)
        tgt_conn = sqlite3.connect(str(tgt_path))
        tgt_conn.row_factory = sqlite3.Row
        tgt_cur = tgt_conn.cursor()

        # Crear tabla de tracking si no existe
        tgt_cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_conversations (
                source TEXT,
                source_rowid INTEGER,
                processed_at DATETIME,
                UNIQUE(source, source_rowid)
            )
        """)
        tgt_conn.commit()

        # Obtener último source_rowid procesado
        tgt_cur.execute("SELECT MAX(source_rowid) as maxid FROM processed_conversations WHERE source = ?", (str(source),))
        row = tgt_cur.fetchone()
        last_processed = int(row['maxid']) if row and row['maxid'] is not None else 0

        # Determinar columna PK en la tabla conversaciones
        try:
            src_cur.execute("PRAGMA table_info(conversaciones)")
            cols_info = src_cur.fetchall()
            pk_cols = [c['name'] for c in cols_info if c[5] == 1]  # c[5] es pk flag
        except Exception:
            pk_cols = []

        # Elegir selector SQL según PK detectada
        if pk_cols:
            pk = pk_cols[0]
            q = f"SELECT * FROM conversaciones WHERE {pk} > ? ORDER BY {pk} ASC"
            params = (last_processed,)
        else:
            # fallback a rowid
            pk = 'rowid'
            q = f"SELECT rowid as rowid, * FROM conversaciones WHERE rowid > ? ORDER BY rowid ASC"
            params = (last_processed,)

        if limit and isinstance(limit, int):
            q = q + f" LIMIT {limit}"

        src_cur.execute(q, params)
        rows = src_cur.fetchall()

        processed = 0
        errors = 0
        last_id = last_processed

        for r in rows:
            try:
                # Determinar id según pk seleccionado
                if pk in r.keys():
                    source_rowid = int(r[pk])
                elif 'rowid' in r.keys():
                    source_rowid = int(r['rowid'])
                else:
                    source_rowid = None
                usuario = r.get('usuario') or r.get('user') or 'unknown'
                pregunta = r.get('consulta') or r.get('pregunta') or r.get('question') or ''
                respuesta = r.get('respuesta') or r.get('answer') or ''

                convo_id = f"src_{source_rowid}"

                # Guardar aprendizaje usando la función existente
                try:
                    save_learning(convo_id, pregunta, respuesta, citations=None, fact_type='conversation')
                except Exception as e:
                    # No detener el proceso
                    errors += 1
                    tgt_cur.execute("INSERT OR IGNORE INTO processed_conversations(source, source_rowid, processed_at) VALUES (?, ?, ?)",
                                    (str(source), source_rowid, datetime.utcnow().isoformat()))
                    tgt_conn.commit()
                    continue

                # Marcar como procesado
                tgt_cur.execute("INSERT OR IGNORE INTO processed_conversations(source, source_rowid, processed_at) VALUES (?, ?, ?)",
                                (str(source), source_rowid, datetime.utcnow().isoformat()))
                tgt_conn.commit()
                processed += 1
                last_id = source_rowid
            except Exception as e:
                errors += 1
                continue

        src_conn.close()
        tgt_conn.close()

        return {'processed': processed, 'errors': errors, 'last_processed_source_id': last_id}

    except Exception as e:
        logger.error(f"❌ ingest_conversations error: {e}")
        return {'processed': 0, 'errors': 1, 'message': str(e)}

