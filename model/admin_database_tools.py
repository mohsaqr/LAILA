#!/usr/bin/env python3
"""
Admin Database Tools for LAILA Chat Logs
Export, query, and manage chat log database
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

class ChatLogDatabase:
    """Class for managing chat log database operations"""
    
    def __init__(self, db_path=.dbchat_logs.db'):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Ensure database exists, create if needed"""
        if not os.path.exists(self.db_path):
            from database_setup import create_chat_logs_database
            create_chat_logs_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def export_to_csv(self, filename=None, date_from=None, date_to=None, module=None, user=None):
        """Export chat logs to CSV with optional filtering"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'chat_logs_export_{timestamp}.csv'
        
        # Build query with filters
        query = "SELECT * FROM chat_logs WHERE 1=1"
        params = []
        
        if date_from:
            query += " AND timestamp >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND timestamp <= ?"
            params.append(date_to)
        
        if module:
            query += " AND module = ?"
            params.append(module)
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        query += " ORDER BY timestamp DESC"
        
        # Execute query and export
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # Remove internal ID column for clean export
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        if 'created_at' in df.columns:
            df = df.drop('created_at', axis=1)
        
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def get_statistics(self):
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM chat_logs")
        stats['total_messages'] = cursor.fetchone()[0]
        
        # Messages by sender
        cursor.execute("SELECT sender, COUNT(*) FROM chat_logs GROUP BY sender")
        stats['by_sender'] = dict(cursor.fetchall())
        
        # Messages by module
        cursor.execute("SELECT module, COUNT(*) FROM chat_logs GROUP BY module ORDER BY COUNT(*) DESC")
        stats['by_module'] = dict(cursor.fetchall())
        
        # Messages by user (top 10)
        cursor.execute("SELECT user, COUNT(*) FROM chat_logs GROUP BY user ORDER BY COUNT(*) DESC LIMIT 10")
        stats['top_users'] = dict(cursor.fetchall())
        
        # Date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM chat_logs")
        date_range = cursor.fetchone()
        stats['date_range'] = {'from': date_range[0], 'to': date_range[1]}
        
        # Recent activity (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM chat_logs WHERE timestamp >= ?", (week_ago,))
        stats['recent_messages'] = cursor.fetchone()[0]
        
        # Average response time
        cursor.execute("SELECT AVG(response_time_sec) FROM chat_logs WHERE sender = 'AI' AND response_time_sec IS NOT NULL")
        avg_response = cursor.fetchone()[0]
        stats['avg_response_time'] = round(avg_response, 2) if avg_response else 0
        
        # Database size
        stats['db_size_bytes'] = os.path.getsize(self.db_path)
        
        conn.close()
        return stats
    
    def get_conversations(self, user=None, module=None, limit=50):
        """Get conversation threads"""
        query = """
            SELECT user, module, timestamp, sender, turn, message, ai_model
            FROM chat_logs 
            WHERE 1=1
        """
        params = []
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        if module:
            query += " AND module = ?"
            params.append(module)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def search_messages(self, search_term, sender=None, module=None, limit=100):
        """Search messages by content"""
        query = """
            SELECT timestamp, user, module, sender, message, context
            FROM chat_logs 
            WHERE message LIKE ?
        """
        params = [f'%{search_term}%']
        
        if sender:
            query += " AND sender = ?"
            params.append(sender)
        
        if module:
            query += " AND module = ?"
            params.append(module)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def cleanup_old_data(self, days_to_keep=365):
        """Remove old data (optional maintenance)"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Count records to be deleted
        cursor.execute("SELECT COUNT(*) FROM chat_logs WHERE timestamp < ?", (cutoff_date,))
        count_to_delete = cursor.fetchone()[0]
        
        if count_to_delete > 0:
            # Delete old records
            cursor.execute("DELETE FROM chat_logs WHERE timestamp < ?", (cutoff_date,))
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            
            conn.commit()
        
        conn.close()
        
        return count_to_delete

def generate_admin_report():
    """Generate comprehensive admin report"""
    db = ChatLogDatabase()
    stats = db.get_statistics()
    
    print("🗄️ LAILA CHAT LOGS DATABASE REPORT")
    print("=" * 60)
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Total Messages: {stats['total_messages']:,}")
    print(f"  Database Size: {stats['db_size_bytes']:,} bytes")
    print(f"  Date Range: {stats['date_range']['from']} to {stats['date_range']['to']}")
    print(f"  Recent Activity (7 days): {stats['recent_messages']:,} messages")
    print(f"  Average AI Response Time: {stats['avg_response_time']} seconds")
    
    print(f"\n👥 MESSAGES BY SENDER:")
    for sender, count in stats['by_sender'].items():
        print(f"  {sender}: {count:,}")
    
    print(f"\n📚 MESSAGES BY MODULE:")
    for module, count in stats['by_module'].items():
        print(f"  {module}: {count:,}")
    
    print(f"\n🏆 TOP USERS:")
    for user, count in list(stats['top_users'].items())[:5]:
        print(f"  {user}: {count:,} messages")
    
    return stats

def export_filtered_data(date_from=None, date_to=None, module=None, user=None):
    """Export filtered data to CSV"""
    db = ChatLogDatabase()
    
    print(f"📤 EXPORTING FILTERED CHAT LOGS")
    print("-" * 40)
    
    if date_from:
        print(f"  From Date: {date_from}")
    if date_to:
        print(f"  To Date: {date_to}")
    if module:
        print(f"  Module: {module}")
    if user:
        print(f"  User: {user}")
    
    filename, count = db.export_to_csv(
        date_from=date_from,
        date_to=date_to,
        module=module,
        user=user
    )
    
    print(f"✅ Exported {count:,} records to: {filename}")
    return filename

if __name__ == "__main__":
    # Generate report
    stats = generate_admin_report()
    
    # Example exports
    print(f"\n📤 EXPORT EXAMPLES:")
    print(f"To export all data: python admin_database_tools.py export_all")
    print(f"To export recent data: python admin_database_tools.py export_recent")
    print(f"To export by module: python admin_database_tools.py export_module 'Data Interpreter'")
    
    # Example of exporting recent data
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    recent_export = export_filtered_data(date_from=week_ago)
    print(f"🎉 Recent data exported to: {recent_export}") 