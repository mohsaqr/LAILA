#!/usr/bin/env python3
"""
SQLite Database Setup for LAILA Chat Logs
Clean, persistent, and research-focused logging
"""

import sqlite3
import os
from datetime import datetime
import pandas as pd

def create_chat_logs_database():
    """Create SQLite database for chat logs with clean schema"""
    
    db_path = 'laila_chat_logs.db'
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create chat_logs table with clean, research-focused schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            user TEXT NOT NULL,
            module TEXT NOT NULL,
            sender TEXT NOT NULL CHECK (sender IN ('User', 'AI')),
            turn INTEGER NOT NULL,
            message TEXT NOT NULL,
            ai_model TEXT,
            response_time_sec REAL,
            context TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON chat_logs(user)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_module ON chat_logs(module)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sender ON chat_logs(sender)')
    
    # Create conversation_sessions table for session tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_sessions (
            session_id TEXT PRIMARY KEY,
            user TEXT NOT NULL,
            module TEXT NOT NULL,
            started_at DATETIME NOT NULL,
            last_activity DATETIME NOT NULL,
            message_count INTEGER DEFAULT 0
        )
    ''')
    
    # Create database metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS database_info (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert database version and creation info
    cursor.execute('''
        INSERT OR REPLACE INTO database_info (key, value, updated_at)
        VALUES ('version', '1.0', ?), ('created', ?, ?)
    ''', (datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Chat logs database created: {db_path}")
    return db_path

def migrate_existing_csv_logs():
    """Migrate existing CSV logs to SQLite database"""
    
    csv_files = ['chat_logs_exhaustive.csv', 'chat_logs_clean.csv']
    migrated_count = 0
    
    conn = sqlite3.connect('laila_chat_logs.db')
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                print(f"📋 Migrating {csv_file}...")
                df = pd.read_csv(csv_file)
                
                # Process based on file type
                if 'exhaustive' in csv_file:
                    # Convert exhaustive format to clean format
                    for _, row in df.iterrows():
                        # Extract essential data only
                        timestamp = row.get('timestamp', datetime.now().isoformat())
                        if 'T' in str(timestamp):  # Convert ISO to readable format
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '')).strftime('%Y-%m-%d %H:%M:%S')
                        
                        user = row.get('user_id', 'unknown')
                        module = str(row.get('chat_type', 'Unknown')).replace('_chat', '').replace('_', ' ').title()
                        sender = 'User' if row.get('message_type') == 'user_input' else 'AI'
                        turn = row.get('conversation_turn', 1)
                        
                        # Get message content (prefer user content for user messages, ai_response for AI)
                        if sender == 'User':
                            message = str(row.get('content', ''))
                        else:
                            message = str(row.get('ai_response', ''))
                        
                        # Clean message
                        message = ' '.join(message.split())[:2000] if message else ''
                        
                        ai_model = row.get('ai_model', '') if sender == 'AI' else ''
                        response_time = round(float(row.get('processing_time_ms', 0)) / 1000, 2) if sender == 'AI' and row.get('processing_time_ms') else None
                        
                        # Extract essential context
                        context_data = str(row.get('context_data', ''))
                        essential_context = extract_essential_context(context_data)
                        
                        # Insert into database
                        conn.execute('''
                            INSERT INTO chat_logs 
                            (timestamp, user, module, sender, turn, message, ai_model, response_time_sec, context)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (timestamp, user, module, sender, turn, message, ai_model, response_time, essential_context))
                        
                        migrated_count += 1
                
                elif 'clean' in csv_file:
                    # Direct migration for clean format
                    for _, row in df.iterrows():
                        conn.execute('''
                            INSERT INTO chat_logs 
                            (timestamp, user, module, sender, turn, message, ai_model, response_time_sec, context)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('timestamp'),
                            row.get('user'),
                            row.get('module'),
                            row.get('sender'),
                            row.get('turn'),
                            row.get('message'),
                            row.get('ai_model'),
                            row.get('response_time_sec'),
                            row.get('context')
                        ))
                        migrated_count += 1
                
                print(f"✅ Migrated {len(df)} entries from {csv_file}")
                
            except Exception as e:
                print(f"⚠️ Error migrating {csv_file}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"🎉 Total migrated entries: {migrated_count}")
    return migrated_count

def extract_essential_context(context_str):
    """Extract only essential research context from context string"""
    if not context_str or context_str == 'nan':
        return ''
    
    # Research-relevant keywords to preserve
    research_keys = ['analysis_type', 'research_context', 'target_insights', 'audience_level', 'user_question']
    essential_parts = []
    
    # Split by | and filter
    parts = str(context_str).split('|')
    for part in parts:
        part = part.strip()
        if any(key in part.lower() for key in research_keys):
            # Clean and limit length
            if ':' in part:
                key, value = part.split(':', 1)
                clean_value = ' '.join(value.strip().split())[:200]
                essential_parts.append(f"{key.strip()}: {clean_value}")
    
    return ' | '.join(essential_parts[:4])  # Limit to 4 most important context items

def test_database():
    """Test database functionality"""
    
    conn = sqlite3.connect('laila_chat_logs.db')
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Database tables: {[table[0] for table in tables]}")
    
    # Get row count
    cursor.execute("SELECT COUNT(*) FROM chat_logs")
    count = cursor.fetchone()[0]
    print(f"📈 Total chat log entries: {count}")
    
    # Show sample data
    if count > 0:
        cursor.execute("SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT 3")
        samples = cursor.fetchall()
        print(f"\n💬 Recent entries:")
        for sample in samples:
            print(f"  [{sample[1]}] {sample[3]} ({sample[4]}): {sample[6][:50]}...")
    
    # Database size
    db_size = os.path.getsize('laila_chat_logs.db')
    print(f"💾 Database size: {db_size:,} bytes")
    
    conn.close()

if __name__ == "__main__":
    print("🗄️ LAILA Chat Logs Database Setup")
    print("=" * 50)
    
    # Create database
    db_path = create_chat_logs_database()
    
    # Migrate existing data
    if os.path.exists('chat_logs_exhaustive.csv'):
        migrate_existing_csv_logs()
    
    # Test database
    test_database()
    
    print(f"\n🎉 Database setup complete!")
    print(f"✅ Persistent chat logs now stored in: {db_path}")
    print(f"✅ Data survives system changes and updates")
    print(f"✅ Can export to CSV anytime from admin interface")
    print(f"✅ Better performance and data integrity") 