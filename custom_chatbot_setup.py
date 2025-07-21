#!/usr/bin/env python3
"""
Custom Chatbot System Setup for LAILA Platform
Allows admins to create and deploy custom chatbots to all users
"""

import sqlite3
import json
from datetime import datetime

def add_chatbot_tables():
    """Add custom chatbot tables to central database"""
    
    conn = sqlite3.connect('laila_central.db')
    cursor = conn.cursor()
    
    # 1. CUSTOM CHATBOTS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_chatbots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            greeting_message TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            ai_service TEXT DEFAULT 'google',
            ai_model TEXT DEFAULT 'gemini-1.5-flash',
            is_active BOOLEAN DEFAULT TRUE,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deployment_settings TEXT,
            usage_count INTEGER DEFAULT 0,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # 2. CHATBOT CONVERSATIONS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatbot_id INTEGER NOT NULL,
            user_id INTEGER,
            session_id TEXT NOT NULL,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            user_feedback TEXT,
            conversation_rating INTEGER,
            FOREIGN KEY (chatbot_id) REFERENCES custom_chatbots (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 3. CHATBOT MESSAGES TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            chatbot_id INTEGER NOT NULL,
            user_id INTEGER,
            sender TEXT NOT NULL CHECK (sender IN ('user', 'chatbot', 'system')),
            message TEXT NOT NULL,
            ai_model TEXT,
            response_time_sec REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            message_context TEXT,
            user_satisfaction INTEGER,
            FOREIGN KEY (conversation_id) REFERENCES chatbot_conversations (id),
            FOREIGN KEY (chatbot_id) REFERENCES custom_chatbots (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 4. CHATBOT ANALYTICS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatbot_id INTEGER NOT NULL,
            date DATE NOT NULL,
            total_conversations INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0,
            unique_users INTEGER DEFAULT 0,
            avg_conversation_length REAL DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            user_satisfaction_avg REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatbot_id) REFERENCES custom_chatbots (id),
            UNIQUE(chatbot_id, date)
        )
    ''')
    
    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_chatbots_active ON custom_chatbots(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_chatbot ON chatbot_conversations(chatbot_id)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_user ON chatbot_conversations(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON chatbot_messages(conversation_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_chatbot ON chatbot_messages(chatbot_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chatbot_messages(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_chatbot_date ON chatbot_analytics(chatbot_id, date)"
    ]
    
    for index in indexes:
        cursor.execute(index)
    
    # Insert a default welcome chatbot
    cursor.execute('''
        INSERT OR IGNORE INTO custom_chatbots 
        (id, name, display_name, description, greeting_message, system_prompt, ai_service, ai_model, is_active)
        VALUES (1, 'welcome_assistant', 'LAILA Welcome Assistant', 
                'A friendly assistant to help new users navigate the LAILA platform',
                'Hello! 👋 Welcome to LAILA! I''m here to help you get started with our platform. You can ask me about our features, how to use different modules, or any questions you have about educational research tools. How can I assist you today?',
                'You are LAILA Welcome Assistant, a helpful and friendly AI assistant for the LAILA educational research platform. Your role is to:\n\n1. Welcome new users warmly\n2. Explain LAILA platform features (Data Interpreter, Prompt Engineering, Bias Analysis, Story Form)\n3. Guide users on how to navigate the platform\n4. Answer questions about educational research tools\n5. Be encouraging and supportive\n6. Keep responses concise but informative\n7. Direct users to appropriate modules when needed\n\nAlways maintain a professional yet friendly tone. If asked about technical issues, suggest contacting support.',
                'google', 'gemini-1.5-flash', 1)
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ Custom chatbot tables created successfully")

def create_sample_chatbots():
    """Create sample chatbots for demonstration"""
    
    conn = sqlite3.connect('laila_central.db')
    cursor = conn.cursor()
    
    sample_chatbots = [
        {
            'name': 'research_helper',
            'display_name': 'Research Methods Helper',
            'description': 'Assists with research methodology questions and statistical analysis guidance',
            'greeting_message': 'Hello! I\'m your Research Methods Helper. I can assist you with research design, statistical analysis, methodology questions, and interpretation of results. What research challenge can I help you with today?',
            'system_prompt': 'You are a Research Methods Helper AI assistant specializing in educational research. Your expertise includes:\n\n1. Research design and methodology\n2. Statistical analysis and interpretation\n3. Data collection methods\n4. Survey design and validation\n5. Qualitative and quantitative research approaches\n6. Literature review strategies\n7. Academic writing and reporting\n\nProvide accurate, methodologically sound advice. Explain complex concepts clearly. When discussing statistical methods, include practical considerations and assumptions. Always encourage best practices in research ethics and methodology.',
            'ai_service': 'google',
            'ai_model': 'gemini-1.5-pro'
        },
        {
            'name': 'writing_tutor',
            'display_name': 'Academic Writing Tutor',
            'description': 'Helps improve academic writing, citations, and paper structure',
            'greeting_message': 'Greetings! I\'m your Academic Writing Tutor. I can help you improve your academic writing, structure your papers, format citations, and develop clear arguments. Whether you\'re working on a research paper, thesis, or publication, I\'m here to guide you. What writing challenge are you facing?',
            'system_prompt': 'You are an Academic Writing Tutor AI assistant focused on helping students and researchers improve their academic writing. Your specialties include:\n\n1. Paper structure and organization\n2. Academic writing style and tone\n3. Citation formats (APA, MLA, Chicago, etc.)\n4. Argument development and logical flow\n5. Grammar and clarity improvements\n6. Thesis and dissertation guidance\n7. Publication and peer review preparation\n\nProvide constructive feedback and specific suggestions. Explain writing principles clearly. Help users develop their own voice while maintaining academic standards. Be encouraging and supportive of the writing process.',
            'ai_service': 'google',
            'ai_model': 'gemini-1.5-flash'
        }
    ]
    
    for chatbot in sample_chatbots:
        cursor.execute('''
            INSERT OR IGNORE INTO custom_chatbots 
            (name, display_name, description, greeting_message, system_prompt, ai_service, ai_model, is_active, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
        ''', (
            chatbot['name'], chatbot['display_name'], chatbot['description'],
            chatbot['greeting_message'], chatbot['system_prompt'],
            chatbot['ai_service'], chatbot['ai_model']
        ))
    
    conn.commit()
    conn.close()
    
    print("✅ Sample chatbots created successfully")

def verify_chatbot_setup():
    """Verify the chatbot system setup"""
    
    conn = sqlite3.connect('laila_central.db')
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%chatbot%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📊 CHATBOT SYSTEM VERIFICATION:")
    print("-" * 50)
    print(f"Tables created: {tables}")
    
    # Check chatbots
    cursor.execute("SELECT COUNT(*) FROM custom_chatbots")
    chatbot_count = cursor.fetchone()[0]
    print(f"Custom chatbots: {chatbot_count}")
    
    if chatbot_count > 0:
        cursor.execute("SELECT display_name, is_active FROM custom_chatbots")
        chatbots = cursor.fetchall()
        print(f"Available chatbots:")
        for name, active in chatbots:
            status = "Active" if active else "Inactive"
            print(f"  - {name} ({status})")
    
    # Database size
    db_size = len(open('laila_central.db', 'rb').read())
    print(f"Database size: {db_size:,} bytes")
    
    conn.close()
    
    print(f"\n🎉 Chatbot system ready!")

if __name__ == "__main__":
    print("🤖 CUSTOM CHATBOT SYSTEM SETUP")
    print("=" * 50)
    
    # Add chatbot tables
    add_chatbot_tables()
    
    # Create sample chatbots
    create_sample_chatbots()
    
    # Verify setup
    verify_chatbot_setup()
    
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Add admin interface for chatbot management")
    print(f"2. Create user interface for chatbot interactions")
    print(f"3. Add API endpoints for chatbot operations")
    print(f"4. Integrate with navigation system") 