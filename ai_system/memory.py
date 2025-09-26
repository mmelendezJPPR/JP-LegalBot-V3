"""Minimal memory helpers for JP-LegalBot - Claude-Mejoras implementation

This module provides lightweight functions used for development/testing only:
- get_user_memory_context: returns last N user messages
- calculate_query_similarity: naive overlap score
- analyze_user_patterns: returns frequent tokens

These are intentionally simple and safe; replace with embeddings/vector search
for production.
"""
import sqlite3
import os
import re
from typing import List, Dict

DB_PATH = os.getenv('CONVERSACIONES_DB', 'conversaciones.db')

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_memory_context(user_id: str, window: int = 5) -> List[Dict]:
    """Return the last `window` conversation entries for a given user."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            'SELECT pregunta AS pregunta, respuesta AS respuesta, timestamp FROM conversaciones WHERE usuario = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, window)
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        # return in chronological order (oldest first)
        return list(reversed(rows))
    except Exception:
        return []

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", (text or '').lower())

def calculate_query_similarity(query: str, contexts: List[Dict]) -> float:
    """Naive similarity: token overlap between query and concatenated contexts."""
    qtokens = set(_tokenize(query))
    if not qtokens:
        return 0.0
    ctx_text = ' '.join((c.get('pregunta','') + ' ' + c.get('respuesta','')) for c in contexts)
    ctx_tokens = set(_tokenize(ctx_text))
    if not ctx_tokens:
        return 0.0
    overlap = qtokens.intersection(ctx_tokens)
    return len(overlap) / max(len(qtokens), 1)

def analyze_user_patterns(user_id: str, top_n: int = 10) -> Dict[str,int]:
    """Return top tokens used by the user across their recent conversations."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute('SELECT pregunta, respuesta FROM conversaciones WHERE usuario = ? ORDER BY timestamp DESC LIMIT 200', (user_id,))
        text = ' '.join((r['pregunta'] or '') + ' ' + (r['respuesta'] or '') for r in cur.fetchall())
        conn.close()
        tokens = _tokenize(text)
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        # return top N
        items = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return {k:v for k,v in items}
    except Exception:
        return {}
