#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestión de Usuarios para JP-LegalBot
Script para agregar, listar y gestionar usuarios
"""

import sqlite3
import os
import hashlib
import getpass
from datetime import datetime

def hash_password(password):
    """Crear hash seguro de password"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password, hash_stored):
    """Verificar password"""
    return hash_password(password) == hash_stored

def add_user():
    """Agregar nuevo usuario interactivamente"""
    db_path = os.path.join("database", "Usuarios.db")
    
    print("\n➕ Agregar Nuevo Usuario")
    print("-" * 30)
    
    email = input("📧 Email: ").strip().lower()
    if not email or "@" not in email:
        print("❌ Email inválido")
        return
    
    password = getpass.getpass("🔑 Password: ")
    if len(password) < 6:
        print("❌ Password debe tener al menos 6 caracteres")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO usuarios (email, password_hash) 
            VALUES (?, ?)
        ''', (email, password_hash))
        
        conn.commit()
        print(f"✅ Usuario creado: {email}")
        
    except sqlite3.IntegrityError:
        print(f"❌ El email {email} ya existe")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

def list_users():
    """Listar todos los usuarios"""
    db_path = os.path.join("database", "Usuarios.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, created_at, is_active, last_login 
            FROM usuarios 
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        
        print(f"\n👥 Total de usuarios: {len(users)}")
        print("=" * 80)
        
        for user in users:
            status = "✅ Activo" if user[3] else "❌ Inactivo"
            last_login = user[4] or "Nunca"
            print(f"ID: {user[0]:<3} | Email: {user[1]:<35} | {status} | Último login: {last_login}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_login():
    """Probar login de usuario"""
    db_path = os.path.join("database", "Usuarios.db")
    
    print("\n🔐 Probar Login")
    print("-" * 20)
    
    email = input("📧 Email: ").strip().lower()
    password = getpass.getpass("🔑 Password: ")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, password_hash, is_active 
            FROM usuarios 
            WHERE email = ?
        ''', (email,))
        
        user = cursor.fetchone()
        
        if not user:
            print("❌ Usuario no encontrado")
            return
        
        if not user[2]:
            print("❌ Usuario desactivado")
            return
        
        if verify_password(password, user[1]):
            # Actualizar último login
            cursor.execute('''
                UPDATE usuarios 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user[0],))
            conn.commit()
            
            print("✅ Login exitoso")
        else:
            print("❌ Password incorrecto")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def delete_user():
    """Menú de eliminación/desactivación de usuarios"""
    db_path = os.path.join("database", "Usuarios.db")
    
    # Mostrar usuarios primero
    list_users()
    
    print("\n🗑️  Gestión de Eliminación de Usuarios")
    print("=" * 40)
    print("1. 🗑️  Eliminar usuario permanentemente")
    print("2. 🚫 Desactivar usuario (recomendado)")
    print("3. ✅ Reactivar usuario")
    print("4. 🔙 Volver al menú principal")
    
    choice = input("\n� Selecciona una opción: ").strip()
    
    if choice == "1":
        delete_user_permanently()
    elif choice == "2":
        deactivate_user()
    elif choice == "3":
        reactivate_user()
    elif choice == "4":
        return
    else:
        print("❌ Opción inválida")

def delete_user_permanently():
    """Eliminar usuario permanentemente"""
    db_path = os.path.join("database", "Usuarios.db")
    
    email = input("\n📧 Email del usuario a ELIMINAR PERMANENTEMENTE: ").strip().lower()
    if not email:
        print("❌ Email requerido")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que existe
        cursor.execute("SELECT id, email FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Usuario no encontrado: {email}")
            conn.close()
            return
        
        print(f"⚠️  ADVERTENCIA: Vas a eliminar PERMANENTEMENTE el usuario '{email}'")
        print("   Esta acción NO se puede deshacer.")
        confirm1 = input("   ¿Continuar? (y/N): ").strip().lower()
        
        if confirm1 not in ['y', 'yes', 'sí', 'si']:
            print("❌ Eliminación cancelada")
            conn.close()
            return
        
        confirm2 = input(f"   Escribe 'ELIMINAR' para confirmar: ").strip()
        
        if confirm2 == 'ELIMINAR':
            cursor.execute("DELETE FROM usuarios WHERE email = ?", (email,))
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Usuario '{email}' eliminado permanentemente")
                
                # Mostrar total restante
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                print(f"📊 Usuarios restantes: {count}")
            else:
                print("❌ No se pudo eliminar")
        else:
            print("❌ Confirmación incorrecta. Eliminación cancelada")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def deactivate_user():
    """Desactivar usuario (recomendado en lugar de eliminar)"""
    db_path = os.path.join("database", "Usuarios.db")
    
    email = input("\n📧 Email del usuario a desactivar: ").strip().lower()
    if not email:
        print("❌ Email requerido")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que existe y está activo
        cursor.execute("SELECT is_active FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Usuario no encontrado: {email}")
            conn.close()
            return
        
        if not user[0]:
            print(f"ℹ️  El usuario '{email}' ya está desactivado")
            conn.close()
            return
        
        # Desactivar usuario
        cursor.execute('''
            UPDATE usuarios 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
            WHERE email = ?
        ''', (email,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Usuario '{email}' desactivado exitosamente")
            print("   (El usuario no podrá hacer login, pero sus datos se preservan)")
        else:
            print("❌ No se pudo desactivar el usuario")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def reactivate_user():
    """Reactivar usuario desactivado"""
    db_path = os.path.join("database", "Usuarios.db")
    
    email = input("\n📧 Email del usuario a reactivar: ").strip().lower()
    if not email:
        print("❌ Email requerido")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que existe y está inactivo
        cursor.execute("SELECT is_active FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Usuario no encontrado: {email}")
            conn.close()
            return
        
        if user[0]:
            print(f"ℹ️  El usuario '{email}' ya está activo")
            conn.close()
            return
        
        # Reactivar usuario
        cursor.execute('''
            UPDATE usuarios 
            SET is_active = 1, updated_at = CURRENT_TIMESTAMP 
            WHERE email = ?
        ''', (email,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Usuario '{email}' reactivado exitosamente")
        else:
            print("❌ No se pudo reactivar el usuario")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main_menu():
    """Menú principal"""
    while True:
        print("\n" + "=" * 50)
        print("🔧 Gestión de Usuarios - JP-LegalBot")
        print("=" * 50)
        print("1. 👥 Listar usuarios")
        print("2. ➕ Agregar usuario")
        print("3. 🔐 Probar login")
        print("4. 🗑️  Eliminar usuario")
        print("5. 🚪 Salir")
        
        choice = input("\n👉 Selecciona una opción: ").strip()
        
        if choice == "1":
            list_users()
        elif choice == "2":
            add_user()
        elif choice == "3":
            test_login()
        elif choice == "4":
            delete_user()
        elif choice == "5":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    # Verificar que existe la base de datos
    db_path = os.path.join("database", "Usuarios.db")
    if not os.path.exists(db_path):
        print("❌ Base de datos no encontrada. Ejecuta primero: py scripts/init_usuarios.py")
    else:
        main_menu()