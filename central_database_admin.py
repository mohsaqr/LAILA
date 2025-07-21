#!/usr/bin/env python3
"""
Central Database Admin Tools for LAILA Platform
Export, query, and manage the central SQLite database
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

class CentralDatabase:
    """Class for managing central database operations"""
    
    def __init__(self, db_path='laila_central.db'):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Ensure database exists, create if needed"""
        if not os.path.exists(self.db_path):
            from central_database_setup import create_central_database
            create_central_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def export_chat_logs(self, filename=None, date_from=None, date_to=None, module=None, user_email=None):
        """Export chat logs to CSV with optional filtering"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'chat_logs_export_{timestamp}.csv'
        
        # Build query with filters and joins
        query = """
            SELECT 
                cl.timestamp,
                u.email as user,
                cl.module,
                cl.sender,
                cl.turn,
                cl.message,
                cl.ai_model,
                cl.response_time_sec,
                cl.context
            FROM chat_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if date_from:
            query += " AND cl.timestamp >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND cl.timestamp <= ?"
            params.append(date_to)
        
        if module:
            query += " AND cl.module = ?"
            params.append(module)
        
        if user_email:
            query += " AND u.email = ?"
            params.append(user_email)
        
        query += " ORDER BY cl.timestamp DESC"
        
        # Execute query and export
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def export_users_data(self, filename=None):
        """Export users data to CSV"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'users_export_{timestamp}.csv'
        
        query = """
            SELECT 
                id,
                fullname,
                email,
                is_admin,
                created_at,
                last_login,
                is_active
            FROM users
            ORDER BY created_at DESC
        """
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Don't include password hashes in export
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def export_user_interactions(self, filename=None, date_from=None, date_to=None, user_email=None):
        """Export user interactions to CSV"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'user_interactions_export_{timestamp}.csv'
        
        query = """
            SELECT 
                ui.timestamp,
                u.email as user,
                ui.interaction_type,
                ui.page,
                ui.action,
                ui.element_id,
                ui.element_type,
                ui.element_value,
                ui.user_agent,
                ui.ip_address
            FROM user_interactions ui
            LEFT JOIN users u ON ui.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if date_from:
            query += " AND ui.timestamp >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND ui.timestamp <= ?"
            params.append(date_to)
        
        if user_email:
            query += " AND u.email = ?"
            params.append(user_email)
        
        query += " ORDER BY ui.timestamp DESC"
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def export_user_submissions(self, filename=None, date_from=None, date_to=None, user_email=None):
        """Export user submissions to CSV"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'user_submissions_export_{timestamp}.csv'
        
        query = """
            SELECT 
                us.submitted_at,
                u.email as user,
                us.submission_type,
                us.vignette_content,
                us.nationality,
                us.gender,
                us.field_of_study,
                us.academic_level
            FROM user_submissions us
            LEFT JOIN users u ON us.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if date_from:
            query += " AND us.submitted_at >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND us.submitted_at <= ?"
            params.append(date_to)
        
        if user_email:
            query += " AND u.email = ?"
            params.append(user_email)
        
        query += " ORDER BY us.submitted_at DESC"
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def export_data_analysis_logs(self, filename=None, date_from=None, date_to=None, user_email=None):
        """Export data analysis logs to CSV"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data_analysis_export_{timestamp}.csv'
        
        query = """
            SELECT 
                dal.timestamp,
                u.email as user,
                dal.analysis_type,
                dal.file_name,
                dal.file_size,
                dal.ai_model,
                dal.processing_time_sec,
                dal.status
            FROM data_analysis_logs dal
            LEFT JOIN users u ON dal.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if date_from:
            query += " AND dal.timestamp >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND dal.timestamp <= ?"
            params.append(date_to)
        
        if user_email:
            query += " AND u.email = ?"
            params.append(user_email)
        
        query += " ORDER BY dal.timestamp DESC"
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        df.to_csv(filename, index=False)
        
        return filename, len(df)
    
    def get_database_statistics(self):
        """Get comprehensive database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM chat_logs")
        stats['total_messages'] = cursor.fetchone()[0]
        
        # Messages by sender
        cursor.execute("SELECT sender, COUNT(*) FROM chat_logs GROUP BY sender")
        stats['by_sender'] = dict(cursor.fetchall())
        
        # Messages by module
        cursor.execute("SELECT module, COUNT(*) FROM chat_logs GROUP BY module ORDER BY COUNT(*) DESC")
        stats['by_module'] = dict(cursor.fetchall())
        
        # Top users by messages
        cursor.execute("""
            SELECT u.email, COUNT(cl.id) as message_count 
            FROM users u 
            LEFT JOIN chat_logs cl ON u.id = cl.user_id 
            GROUP BY u.id 
            ORDER BY message_count DESC 
            LIMIT 10
        """)
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
        
        # User interactions count
        cursor.execute("SELECT COUNT(*) FROM user_interactions")
        stats['total_interactions'] = cursor.fetchone()[0]
        
        # User submissions count
        cursor.execute("SELECT COUNT(*) FROM user_submissions")
        stats['total_submissions'] = cursor.fetchone()[0]
        
        # Database size
        stats['db_size_bytes'] = os.path.getsize(self.db_path)
        
        conn.close()
        return stats
    
    def search_messages(self, search_term, sender=None, module=None, user_email=None, limit=100):
        """Search messages by content"""
        query = """
            SELECT 
                cl.timestamp,
                u.email as user,
                cl.module,
                cl.sender,
                cl.message,
                cl.context
            FROM chat_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            WHERE cl.message LIKE ?
        """
        params = [f'%{search_term}%']
        
        if sender:
            query += " AND cl.sender = ?"
            params.append(sender)
        
        if module:
            query += " AND cl.module = ?"
            params.append(module)
        
        if user_email:
            query += " AND u.email = ?"
            params.append(user_email)
        
        query += " ORDER BY cl.timestamp DESC LIMIT ?"
        params.append(limit)
        
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_user_by_email(self, email):
        """Get user information by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, fullname, email, is_admin, created_at, last_login FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'fullname': user[1],
                'email': user[2],
                'is_admin': user[3],
                'created_at': user[4],
                'last_login': user[5]
            }
        return None
    
    def update_user_last_login(self, email):
        """Update user's last login time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET last_login = ? WHERE email = ?", 
                      (datetime.now().isoformat(), email))
        
        conn.commit()
        conn.close()

def generate_comprehensive_report():
    """Generate comprehensive admin report"""
    db = CentralDatabase()
    stats = db.get_database_statistics()
    
    print("🗄️ LAILA CENTRAL DATABASE REPORT")
    print("=" * 60)
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Total Users: {stats['total_users']:,}")
    print(f"  Total Messages: {stats['total_messages']:,}")
    print(f"  Total Interactions: {stats['total_interactions']:,}")
    print(f"  Total Submissions: {stats['total_submissions']:,}")
    print(f"  Database Size: {stats['db_size_bytes']:,} bytes")
    
    if stats['date_range']['from']:
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
    for email, count in list(stats['top_users'].items())[:5]:
        print(f"  {email}: {count:,} messages")
    
    return stats

if __name__ == "__main__":
    # Generate report
    stats = generate_comprehensive_report()
    
    # Example exports
    print(f"\n📤 TESTING EXPORT FUNCTIONALITY:")
    
    db = CentralDatabase()
    
    # Test chat logs export
    try:
        filename, count = db.export_chat_logs()
        print(f"✅ Chat logs exported: {count} records to {filename}")
        os.remove(filename)  # Clean up
    except Exception as e:
        print(f"❌ Chat logs export failed: {e}")
    
    # Test users export
    try:
        filename, count = db.export_users_data()
        print(f"✅ Users data exported: {count} records to {filename}")
        os.remove(filename)  # Clean up
    except Exception as e:
        print(f"❌ Users export failed: {e}")
    
    # Test interactions export
    try:
        filename, count = db.export_user_interactions()
        print(f"✅ User interactions exported: {count} records to {filename}")
        os.remove(filename)  # Clean up
    except Exception as e:
        print(f"❌ Interactions export failed: {e}")
    
    print(f"\n🎉 Central database is fully functional!") 