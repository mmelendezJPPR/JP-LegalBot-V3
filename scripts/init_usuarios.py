#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inicializar Base de Datos de Usuarios para JP-LegalBot
Crea la tabla usuarios en database/Usuarios.db
"""

import sqlite3
import os
import sys
import hashlib
from datetime import datetime

def init_usuarios_db():
    """Crear la base de datos de usuarios con tabla segura"""
    
    # Ruta de la base de datos
    db_path = os.path.join("database", "Usuarios.db")
    
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tabla usuarios con campos básicos y seguros
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP NULL
            )
        ''')
        
        # Crear índice en email para búsquedas rápidas
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)
        ''')
        
        # Crear trigger para actualizar timestamp
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_usuarios_timestamp 
            AFTER UPDATE ON usuarios
            FOR EACH ROW
            BEGIN
                UPDATE usuarios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')
        
        conn.commit()
        print("✅ Tabla 'usuarios' creada exitosamente en database/Usuarios.db")
        print(f"📁 Ubicación: {os.path.abspath(db_path)}")
        
        # Mostrar estructura de la tabla
        cursor.execute("PRAGMA table_info(usuarios)")
        columns = cursor.fetchall()
        
        print("\n📊 Estructura de la tabla 'usuarios':")
        print("=" * 60)
        for col in columns:
            print(f"  {col[1]:<15} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando base de datos: {e}")
        return False

def hash_password(password):
    """Crear hash seguro de password"""
    # Usar SHA-256 por simplicidad (en producción usar bcrypt)
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def add_test_user():
    """Agregar usuario de prueba"""
    db_path = os.path.join("database", "Usuarios.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Usuario de prueba
        test_email = "admin@juntaplanificacion.pr.gov"
        test_password = "admin123"
        password_hash = hash_password(test_password)
        
        cursor.execute('''
            INSERT OR IGNORE INTO usuarios (email, password_hash) 
            VALUES (?, ?)
        ''', (test_email, password_hash))
        
        if cursor.rowcount > 0:
            print(f"✅ Usuario de prueba creado: {test_email}")
            print(f"🔑 Password: {test_password}")
        else:
            print(f"ℹ️  Usuario ya existe: {test_email}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error agregando usuario de prueba: {e}")

def verify_database():
    """Verificar que la base de datos funcione correctamente"""
    db_path = os.path.join("database", "Usuarios.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Contar usuarios
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        
        print(f"\n📈 Total de usuarios en la base: {count}")
        
        # Mostrar usuarios (sin passwords)
        cursor.execute("SELECT id, email, created_at, is_active FROM usuarios")
        users = cursor.fetchall()
        
        if users:
            print("\n👥 Usuarios registrados:")
            print("-" * 60)
            for user in users:
                status = "✅ Activo" if user[3] else "❌ Inactivo"
                print(f"  ID: {user[0]} | Email: {user[1]} | {status}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verificando base de datos: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Inicializando Base de Datos de Usuarios - JP-LegalBot")
    print("=" * 60)
    
    # Crear tabla usuarios
    if init_usuarios_db():
        # Agregar usuario de prueba
        add_test_user()
        
        # Verificar base de datos
        verify_database()
        
        print("\n" + "=" * 60)
        print("✅ Base de datos de usuarios lista para usar")
        print("=" * 60)
    else:
        print("\n❌ Error inicializando base de datos")
        sys.exit(1)