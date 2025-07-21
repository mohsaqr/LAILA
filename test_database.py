#!/usr/bin/env python3
"""Quick test of database functionality"""

import sqlite3

def test_databases():
    print("🔍 Testing LAILA Database System...")
    
    # Test system database
    try:
        conn = sqlite3.connect('laila_system.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM system_settings")
        settings_count = cursor.fetchone()[0]
        print(f"✅ System settings: {settings_count}")
        
        cursor.execute("SELECT COUNT(*) FROM system_chatbots")
        chatbots_count = cursor.fetchone()[0]
        print(f"✅ System chatbots: {chatbots_count}")
        
        cursor.execute("SELECT name, display_name FROM system_chatbots WHERE is_active = 1")
        chatbots = cursor.fetchall()
        for name, display_name in chatbots:
            print(f"   - {display_name} ({name})")
        
        conn.close()
    except Exception as e:
        print(f"❌ System database error: {e}")
    
    # Test user database
    try:
        conn = sqlite3.connect('laila_user.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"✅ Users: {users_count}")
        
        conn.close()
    except Exception as e:
        print(f"❌ User database error: {e}")
    
    print("🎉 Database test complete!")

if __name__ == "__main__":
    test_databases()
