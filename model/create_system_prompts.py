
import sqlite3
import os
from datetime import datetime
import bcrypt
import argparse

def create_system_prompts():
    """Create system prompts in the SQLite database"""
    
    db_path = 'db/laila_central.db'
    
    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. USERS TABLE (from users.csv)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            prompt TEXT UNIQUE NOT NULL
        )
    ''')

    prompt_files = {
        'bias_analyst': 'bias-analysis-system-prompt.txt',
        'bias_analysis': 'bias-analysis-system-prompt.txt',
        'prompt_helper': 'prompt-helper-system-prompt.txt',
        'data_interpreter': 'interpret-data-system-prompt.txt',
        'research_helper': 'research-helper-system-prompt.txt',
        'welcome_assistant': 'welcome-assistant-system-prompt.txt'
    }
    for prompt_name in prompt_files:
    
        filename = "prompts/" + prompt_files.get(prompt_name)
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"✅ Loaded prompt '{prompt_name}' from {filename} ({len(content)} chars)")
                cursor.execute('''
                    INSERT INTO system_prompts 
                    (name, prompt)
                    VALUES (?, ?)
                ''', (prompt_name, content))
                print(content)

        except FileNotFoundError:
            print(f"Prompt file not found: {filename}. Please ensure the file exists.")
        except Exception as e:
            print(f"Error loading prompt from {filename}: {str(e)}")
    conn.commit()

if __name__ == "__main__":
    print("SYSTEM PROMPTS CREATION SCRIPT")
    
    
    # Add chatbot tables
    create_system_prompts()

