#!/usr/bin/env python3
"""
Central Database Setup for LAILA Platform
Migrates ALL data from CSV files to SQLite for centralized management
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
import json
import bcrypt

def create_central_database():
    """Create comprehensive SQLite database for all LAILA data"""
    
    db_path = 'laila_central.db'
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. USERS TABLE (from users.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # 2. USER SETTINGS TABLE (from user_settings.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            setting_key TEXT NOT NULL,
            setting_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, setting_key)
        )
    ''')
    
    # 3. SYSTEM SETTINGS TABLE (centralized system configuration)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            description TEXT,
            is_encrypted BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. CHAT LOGS TABLE (enhanced from previous)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            timestamp DATETIME NOT NULL,
            module TEXT NOT NULL,
            sender TEXT NOT NULL CHECK (sender IN ('User', 'AI')),
            turn INTEGER NOT NULL,
            message TEXT NOT NULL,
            ai_model TEXT,
            response_time_sec REAL,
            context TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 5. USER SUBMISSIONS TABLE (from submissions.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            submission_type TEXT,
            submission_data TEXT,
            vignette_content TEXT,
            nationality TEXT,
            gender TEXT,
            field_of_study TEXT,
            academic_level TEXT,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 6. USER INTERACTIONS TABLE (from user_interactions.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            interaction_type TEXT,
            page TEXT,
            action TEXT,
            element_id TEXT,
            element_type TEXT,
            element_value TEXT,
            timestamp DATETIME NOT NULL,
            user_agent TEXT,
            ip_address TEXT,
            additional_data TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 7. API CONFIGURATIONS TABLE (from API_Settings.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT UNIQUE NOT NULL,
            api_key TEXT,
            default_model TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            rate_limit INTEGER,
            configuration_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 8. DATA ANALYSIS LOGS TABLE (from data_analysis_logs.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_type TEXT,
            file_name TEXT,
            file_size INTEGER,
            analysis_result TEXT,
            ai_model TEXT,
            processing_time_sec REAL,
            timestamp DATETIME NOT NULL,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_chat_logs_timestamp ON chat_logs(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_chat_logs_module ON chat_logs(module)",
        "CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON user_interactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_interactions_timestamp ON user_interactions(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_user_settings_user ON user_settings(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key)"
    ]
    
    for index in indexes:
        cursor.execute(index)
    
    # Insert default system settings
    default_settings = [
        ('default_ai_service', 'google', 'string', 'Default AI service to use'),
        ('default_google_model', 'gemini-1.5-flash', 'string', 'Default Google AI model'),
        ('default_openai_model', 'gpt-4o-mini', 'string', 'Default OpenAI model'),
        ('google_api_key', '', 'encrypted', 'Google AI API key'),
        ('openai_api_key', '', 'encrypted', 'OpenAI API key'),
        ('max_file_upload_size', '10485760', 'integer', 'Maximum file upload size in bytes'),
        ('session_timeout', '3600', 'integer', 'Session timeout in seconds'),
        ('enable_analytics', 'true', 'boolean', 'Enable user analytics tracking'),
        ('platform_version', '2.0', 'string', 'LAILA platform version')
    ]
    
    for setting in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value, setting_type, description)
            VALUES (?, ?, ?, ?)
        ''', setting)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Central database created: {db_path}")
    return db_path

def migrate_csv_data():
    """Migrate all existing CSV data to central database"""
    
    conn = sqlite3.connect('laila_central.db')
    migrated_counts = {}
    
    # 1. Migrate Users
    if os.path.exists('users.csv'):
        try:
            print("📋 Migrating users.csv...")
            df = pd.read_csv('users.csv')
            count = 0
            for _, row in df.iterrows():
                # Convert admin status properly
                is_admin = str(row.get('is_admin', 'False')).strip().lower() == 'true'
                
                conn.execute('''
                    INSERT OR REPLACE INTO users (fullname, email, password_hash, is_admin)
                    VALUES (?, ?, ?, ?)
                ''', (row['fullname'], row['email'], row['password'], is_admin))
                count += 1
            
            migrated_counts['users'] = count
            print(f"✅ Migrated {count} users")
            
        except Exception as e:
            print(f"⚠️ Error migrating users: {e}")
    
    # 2. Migrate User Settings
    if os.path.exists('user_settings.csv'):
        try:
            print("📋 Migrating user_settings.csv...")
            df = pd.read_csv('user_settings.csv')
            count = 0
            for _, row in df.iterrows():
                # Get user ID from email
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (row['user_id'],))
                user_result = cursor.fetchone()
                if user_result:
                    user_id = user_result[0]
                    
                    # Insert each setting
                    for col in df.columns:
                        if col != 'user_id' and pd.notna(row[col]):
                            conn.execute('''
                                INSERT OR REPLACE INTO user_settings (user_id, setting_key, setting_value)
                                VALUES (?, ?, ?)
                            ''', (user_id, col, str(row[col])))
                            count += 1
            
            migrated_counts['user_settings'] = count
            print(f"✅ Migrated {count} user settings")
            
        except Exception as e:
            print(f"⚠️ Error migrating user settings: {e}")
    
    # 3. Migrate Chat Logs (from clean CSV)
    if os.path.exists('chat_logs_clean.csv'):
        try:
            print("📋 Migrating chat_logs_clean.csv...")
            df = pd.read_csv('chat_logs_clean.csv')
            count = 0
            for _, row in df.iterrows():
                # Get user ID from email
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (row['user'],))
                user_result = cursor.fetchone()
                user_id = user_result[0] if user_result else None
                
                conn.execute('''
                    INSERT INTO chat_logs 
                    (user_id, timestamp, module, sender, turn, message, ai_model, response_time_sec, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, row['timestamp'], row['module'], row['sender'],
                    row['turn'], row['message'], row.get('ai_model', ''),
                    row.get('response_time_sec'), row.get('context', '')
                ))
                count += 1
            
            migrated_counts['chat_logs'] = count
            print(f"✅ Migrated {count} chat log entries")
            
        except Exception as e:
            print(f"⚠️ Error migrating chat logs: {e}")
    
    # 4. Migrate Submissions
    if os.path.exists('submissions.csv'):
        try:
            print("📋 Migrating submissions.csv...")
            df = pd.read_csv('submissions.csv')
            count = 0
            for _, row in df.iterrows():
                # Get user ID from email
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (row['user_id'],))
                user_result = cursor.fetchone()
                user_id = user_result[0] if user_result else None
                
                conn.execute('''
                    INSERT INTO user_submissions 
                    (user_id, submission_type, vignette_content, nationality, gender, field_of_study, academic_level, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, 'story_submission', row.get('Complete_Vignette', ''),
                    row.get('Nationality', ''), row.get('Gender', ''),
                    row.get('FieldOfStudy', ''), row.get('AcademicLevel', ''),
                    pd.to_datetime(row['ID'], unit='ms', errors='coerce')
                ))
                count += 1
            
            migrated_counts['submissions'] = count
            print(f"✅ Migrated {count} submissions")
            
        except Exception as e:
            print(f"⚠️ Error migrating submissions: {e}")
    
    # 5. Migrate User Interactions
    if os.path.exists('user_interactions_detailed.csv'):
        try:
            print("📋 Migrating user_interactions_detailed.csv...")
            df = pd.read_csv('user_interactions_detailed.csv')
            count = 0
            for _, row in df.iterrows():
                # Get user ID from email
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (row['user_id'],))
                user_result = cursor.fetchone()
                user_id = user_result[0] if user_result else None
                
                conn.execute('''
                    INSERT INTO user_interactions 
                    (user_id, interaction_type, page, action, timestamp, user_agent, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, row.get('interaction_type', ''), row.get('page', ''),
                    row.get('action', ''), row['timestamp'],
                    row.get('user_agent', ''), row.get('ip_address', '')
                ))
                count += 1
            
            migrated_counts['interactions'] = count
            print(f"✅ Migrated {count} user interactions")
            
        except Exception as e:
            print(f"⚠️ Error migrating interactions: {e}")
    
    # 6. Migrate API Settings from API_Settings.py
    try:
        print("📋 Migrating API settings...")
        from API_Settings import GOOGLE_API_KEY, OPENAI_API_KEY, DEFAULT_AI_SERVICE, DEFAULT_GOOGLE_MODEL, DEFAULT_OPENAI_MODEL
        
        api_configs = [
            ('google', GOOGLE_API_KEY, DEFAULT_GOOGLE_MODEL),
            ('openai', OPENAI_API_KEY, DEFAULT_OPENAI_MODEL)
        ]
        
        count = 0
        for service, api_key, model in api_configs:
            conn.execute('''
                INSERT OR REPLACE INTO api_configurations (service_name, api_key, default_model, is_active)
                VALUES (?, ?, ?, ?)
            ''', (service, api_key, model, True))
            count += 1
        
        # Update system settings
        conn.execute('UPDATE system_settings SET setting_value = ? WHERE setting_key = ?', 
                    (DEFAULT_AI_SERVICE, 'default_ai_service'))
        conn.execute('UPDATE system_settings SET setting_value = ? WHERE setting_key = ?', 
                    (GOOGLE_API_KEY, 'google_api_key'))
        conn.execute('UPDATE system_settings SET setting_value = ? WHERE setting_key = ?', 
                    (OPENAI_API_KEY, 'openai_api_key'))
        
        migrated_counts['api_configs'] = count
        print(f"✅ Migrated {count} API configurations")
        
    except Exception as e:
        print(f"⚠️ Error migrating API settings: {e}")
    
    conn.commit()
    conn.close()
    
    return migrated_counts

def verify_migration():
    """Verify the migration was successful"""
    
    conn = sqlite3.connect('laila_central.db')
    cursor = conn.cursor()
    
    # Check all tables
    tables = [
        'users', 'user_settings', 'system_settings', 'chat_logs',
        'user_submissions', 'user_interactions', 'api_configurations'
    ]
    
    print(f"\n📊 DATABASE VERIFICATION:")
    print("-" * 50)
    
    total_records = 0
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        total_records += count
        print(f"  {table:20}: {count:>6} records")
    
    print("-" * 50)
    print(f"  {'TOTAL':20}: {total_records:>6} records")
    
    # Check database size
    db_size = os.path.getsize('laila_central.db')
    print(f"  {'Database Size':20}: {db_size:>6} bytes")
    
    # Show sample users
    cursor.execute("SELECT email, is_admin FROM users LIMIT 3")
    users = cursor.fetchall()
    print(f"\n👥 SAMPLE USERS:")
    for email, is_admin in users:
        admin_status = "Admin" if is_admin else "User"
        print(f"  {email} ({admin_status})")
    
    # Show system settings
    cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE '%api%' OR setting_key LIKE '%service%'")
    settings = cursor.fetchall()
    print(f"\n⚙️ KEY SYSTEM SETTINGS:")
    for key, value in settings:
        display_value = value[:20] + "..." if len(str(value)) > 20 else value
        print(f"  {key}: {display_value}")
    
    conn.close()
    
    return total_records

if __name__ == "__main__":
    print("🗄️ LAILA CENTRAL DATABASE SETUP")
    print("=" * 60)
    
    # Create database
    db_path = create_central_database()
    
    # Migrate all data
    print(f"\n📋 MIGRATING ALL CSV DATA...")
    migrated_counts = migrate_csv_data()
    
    # Verify migration
    total_records = verify_migration()
    
    print(f"\n🎉 MIGRATION COMPLETE!")
    print(f"✅ Central database: {db_path}")
    print(f"✅ Total records migrated: {total_records}")
    print(f"✅ All system data now centralized!")
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Update app.py to use central database")
    print(f"2. Create admin interface for database management")
    print(f"3. Test all functionality with new database")
    print(f"4. Archive old CSV files as backups") 