#!/usr/bin/env python3
"""Setup LAILA Two-Database System"""

import sqlite3
import json
import bcrypt

def create_system_database():
    conn = sqlite3.connect('laila_system.db')
    cursor = conn.cursor()
    
    # System settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            description TEXT
        )
    ''')
    
    # System chatbots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_chatbots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            greeting_message TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            ai_service TEXT DEFAULT 'google',
            ai_model TEXT DEFAULT 'gemini-1.5-flash',
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Module configurations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS module_configurations (
            module_name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            ai_service TEXT DEFAULT 'google',
            ai_model TEXT DEFAULT 'gemini-1.5-flash',
            configuration_data TEXT
        )
    ''')
    
    # Insert system settings
    settings = [
        ('default_ai_service', 'google', 'string', 'Default AI service'),
        ('default_google_model', 'gemini-1.5-flash', 'string', 'Default Google model'),
        ('default_openai_model', 'gpt-4o-mini', 'string', 'Default OpenAI model'),
        ('enable_test_mode', 'true', 'boolean', 'Enable test mode when no API keys'),
    ]
    
    for setting_key, setting_value, setting_type, description in settings:
        cursor.execute('''
            INSERT OR REPLACE INTO system_settings (setting_key, setting_value, setting_type, description)
            VALUES (?, ?, ?, ?)
        ''', (setting_key, setting_value, setting_type, description))
    
    # Insert bias analyst chatbot
    cursor.execute('''
        INSERT OR REPLACE INTO system_chatbots 
        (name, display_name, description, greeting_message, system_prompt, ai_service, ai_model, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    ''', (
        'bias_analyst',
        'Bias Analysis Expert',
        'Specialized in detecting and analyzing various forms of bias',
        'Hello! I\'m the Bias Analysis Expert. I can help you examine bias in stories, research designs, and data. What would you like me to analyze?',
        '''You are a Bias Analysis Expert specializing in educational research. Your expertise includes:

1. Detecting gender, cultural, and socioeconomic bias
2. Analyzing bias in research design and methodology  
3. Identifying confirmation bias and selection bias
4. Examining bias in data interpretation
5. Recognizing implicit bias in narratives and case studies
6. Providing strategies to minimize bias
7. Promoting inclusive and equitable research practices

When analyzing content for bias, be thorough but balanced. Explain your reasoning clearly and suggest concrete steps for improvement.''',
        'google',
        'gemini-1.5-pro'
    ))
    
    # Insert module configurations
    modules = [
        ('bias_analysis', 'Bias Analysis', True, 'google', 'gemini-1.5-pro'),
        ('prompt_helper', 'Prompt Engineering', True, 'google', 'gemini-1.5-flash'),
        ('data_interpreter', 'Data Interpreter', True, 'google', 'gemini-1.5-flash'),
    ]
    
    for module_name, display_name, enabled, ai_service, ai_model in modules:
        config_data = json.dumps({'max_turns': 50, 'temperature': 0.7})
        cursor.execute('''
            INSERT OR REPLACE INTO module_configurations 
            (module_name, display_name, is_enabled, ai_service, ai_model, configuration_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (module_name, display_name, enabled, ai_service, ai_model, config_data))
    
    conn.commit()
    conn.close()
    print("✅ System database created")

def create_user_database():
    conn = sqlite3.connect('laila_user.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Chat logs table
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
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert default admin user
    password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute('''
        INSERT OR IGNORE INTO users (fullname, email, password_hash, is_admin, is_active)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Administrator', 'admin@laila.platform', password_hash, True, True))
    
    conn.commit()
    conn.close()
    print("✅ User database created")

if __name__ == "__main__":
    print("🗄️ LAILA DATABASE SETUP")
    create_system_database()
    create_user_database()
    print("🎉 Setup complete!")
