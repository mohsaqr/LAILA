from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory, send_file, render_template_string
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import sqlite3
import pandas as pd
import openai
import google.generativeai as genai
from config import get_ai_configuration, LOGIN_TEMPLATE, CHAT_SYSTEM_PROMPT, load_bias_analysis_prompt
from API_Settings import GOOGLE_API_KEY, OPENAI_API_KEY, DEFAULT_AI_SERVICE, DEFAULT_GOOGLE_MODEL, DEFAULT_OPENAI_MODEL, is_service_available
import bcrypt
import uuid
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime, timedelta
import random
import csv
import time
import traceback
import sys

# Enhanced logging functions
def log_chat_interaction(user_id, chat_type, message_type, content, context_data=None, ai_model=None, ai_response=None, processing_time=None):
    """Log chat interactions to central SQLite database - persistent and reliable"""
    try:
        import sqlite3
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_id = session.get('chat_id', str(uuid.uuid4()))
        
        # Ensure chat_id is set in session
        if 'chat_id' not in session:
            session['chat_id'] = chat_id
        
        # Track conversation turns
        turn_key = f'turn_count_{chat_id}'
        current_turn = session.get(turn_key, 1)
        if message_type == 'user_input':
            session[turn_key] = current_turn + 1

        # Clean message content
        def clean_message(text):
            if text is None:
                return ""
            # Remove extra whitespace and newlines
            cleaned = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            cleaned = ' '.join(cleaned.split())  # Remove multiple spaces
            return cleaned[:2000] if len(cleaned) > 2000 else cleaned  # Reasonable limit

        # Extract essential context only
        essential_context = ""
        if context_data and isinstance(context_data, dict):
            # Keep only research-relevant context
            research_keys = ['analysis_type', 'research_context', 'target_insights', 'audience_level']
            context_items = []
            for key in research_keys:
                if key in context_data and context_data[key]:
                    value = str(context_data[key])[:200]  # Limit length
                    context_items.append(f"{key}: {value}")
            essential_context = " | ".join(context_items)

        # Get user database ID from email
        user_db_id = None
        try:
            from central_database_admin import CentralDatabase
            db = CentralDatabase()
            user_info = db.get_user_by_email(user_id)
            if user_info:
                user_db_id = user_info['id']
        except:
            pass

        # Prepare data for database
        module = chat_type.replace('_chat', '').replace('_', ' ').title()
        sender = 'User' if message_type == 'user_input' else 'AI'
        turn = session.get(turn_key, 1)
        message = clean_message(content if message_type == 'user_input' else ai_response)
        ai_model_used = ai_model if message_type == 'ai_response' else ''
        response_time = round(processing_time / 1000, 2) if processing_time and message_type == 'ai_response' else None
        context = essential_context

        # Save to Central SQLite database
        db_path = 'laila_central.db'
        
        # Ensure database exists
        if not os.path.exists(db_path):
            from central_database_setup import create_central_database
            create_central_database()
        
        # Insert into central database
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO chat_logs 
            (user_id, session_id, timestamp, module, sender, turn, message, ai_model, response_time_sec, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_db_id, chat_id, timestamp, module, sender, turn, message, ai_model_used, response_time, context))
        
        conn.commit()
        conn.close()
        
        # Also create CSV backup for immediate access (optional fallback)
        try:
            log_entry = {
                'timestamp': timestamp, 'user': user_id, 'module': module, 'sender': sender,
                'turn': turn, 'message': message, 'ai_model': ai_model_used, 
                'response_time_sec': response_time, 'context': context
            }
            
            clean_logs_file = 'chat_logs_clean.csv'
            df = pd.DataFrame([log_entry])
            
            if os.path.exists(clean_logs_file):
                df.to_csv(clean_logs_file, mode='a', header=False, index=False, encoding='utf-8')
            else:
                df.to_csv(clean_logs_file, index=False, encoding='utf-8')
        except:
            pass  # SQLite is primary, CSV is just backup
        
    except Exception as e:
        print(f"Error logging chat interaction to central database: {str(e)}")
        # Fallback to CSV if database fails
        try:
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user': user_id,
                'module': chat_type.replace('_chat', '').replace('_', ' ').title(),
                'sender': 'User' if message_type == 'user_input' else 'AI',
                'turn': session.get(f'turn_count_{session.get("chat_id", "unknown")}', 1),
                'message': content if message_type == 'user_input' else ai_response,
                'ai_model': ai_model if message_type == 'ai_response' else '',
                'response_time_sec': round(processing_time / 1000, 2) if processing_time and message_type == 'ai_response' else '',
                'context': str(context_data) if context_data else ''
            }
            
            df = pd.DataFrame([log_entry])
            df.to_csv('chat_logs_fallback.csv', mode='a', header=not os.path.exists('chat_logs_fallback.csv'), index=False)
        except:
            pass

# Keep original function for technical logs (renamed for system debugging)
def log_chat_interaction_detailed(user_id, chat_type, message_type, content, context_data=None, ai_model=None, ai_response=None, processing_time=None):
    """Log all chat interactions with exhaustive technical details for debugging"""
    try:
        timestamp = datetime.now().isoformat()
        session_id = session.get('session_id', str(uuid.uuid4()))
        chat_id = session.get('chat_id', str(uuid.uuid4()))
        
        # Ensure chat_id is set in session
        if 'chat_id' not in session:
            session['chat_id'] = chat_id
        
        # Clean and prepare content for CSV
        def clean_for_csv(text):
            if text is None:
                return ""
            cleaned = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            cleaned = ' '.join(cleaned.split())
            return cleaned[:5000] if len(cleaned) > 5000 else cleaned
        
        # Clean context data
        context_str = ""
        if context_data:
            try:
                context_items = []
                for key, value in context_data.items():
                    if value is not None:
                        context_items.append(f"{key}:{clean_for_csv(str(value))}")
                context_str = " | ".join(context_items)
            except:
                context_str = "context_error"
        
        log_entry = {
            'timestamp': timestamp,
            'user_id': user_id,
            'session_id': session_id,
            'chat_id': chat_id,
            'chat_type': chat_type,
            'message_type': message_type,
            'content': clean_for_csv(content),
            'content_length': len(content) if content else 0,
            'ai_model': ai_model or "",
            'ai_response': clean_for_csv(ai_response),
            'ai_response_length': len(ai_response) if ai_response else 0,
            'processing_time_ms': processing_time or 0,
            'context_data': context_str,
            'user_agent': request.headers.get('User-Agent', '')[:200],
            'ip_address': request.remote_addr,
            'page_url': request.url[:500],
            'request_method': request.method
        }
        
        # Save to detailed logs for debugging (only if needed)
        debug_logs_file = 'chat_logs_debug.csv'
        df = pd.DataFrame([log_entry])
        
        if os.path.exists(debug_logs_file):
            df.to_csv(debug_logs_file, mode='a', header=False, index=False, encoding='utf-8')
        else:
            df.to_csv(debug_logs_file, index=False, encoding='utf-8')
        
    except Exception as e:
        print(f"Error logging detailed chat interaction: {str(e)}")

def log_data_analysis(user_id, analysis_type, input_data, generated_data, ai_model=None, processing_time=None, additional_context=None):
    """Log data analysis operations with full details using proper CSV format"""
    try:
        timestamp = datetime.now().isoformat()
        session_id = session.get('session_id', str(uuid.uuid4()))
        
        # Clean and prepare content for CSV
        def clean_for_csv(text):
            if text is None:
                return ""
            # Replace newlines with spaces and clean up extra whitespace
            cleaned = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # Remove multiple spaces
            cleaned = ' '.join(cleaned.split())
            # Truncate if too long to prevent CSV issues
            return cleaned[:3000] if len(cleaned) > 3000 else cleaned
        
        # Clean context data
        context_str = ""
        if additional_context:
            try:
                # Convert context to a simple string representation
                context_items = []
                for key, value in additional_context.items():
                    if value is not None:
                        context_items.append(f"{key}:{clean_for_csv(str(value))}")
                context_str = " | ".join(context_items)
            except:
                context_str = "context_error"
        
        log_entry = {
            'timestamp': timestamp,
            'user_id': user_id,
            'session_id': session_id,
            'analysis_type': analysis_type,
            'input_data_type': type(input_data).__name__,
            'input_data_length': len(str(input_data)) if input_data else 0,
            'input_data_sample': clean_for_csv(input_data),
            'generated_data_type': type(generated_data).__name__,
            'generated_data_length': len(str(generated_data)) if generated_data else 0,
            'generated_data_sample': clean_for_csv(generated_data),
            'ai_model': ai_model or "",
            'processing_time_ms': processing_time or 0,
            'additional_context': context_str,
            'user_agent': request.headers.get('User-Agent', '')[:200],  # Truncate long user agents
            'ip_address': request.remote_addr,
            'page_url': request.url[:500]  # Truncate long URLs
        }
        
        # Save to data analysis logs CSV with proper encoding and quoting
        analysis_logs_file = 'data_analysis_logs.csv'
        df = pd.DataFrame([log_entry])
        
        if os.path.exists(analysis_logs_file):
            # Append to existing file
            df.to_csv(analysis_logs_file, mode='a', header=False, index=False, 
                     quoting=1,  # QUOTE_ALL - quote all fields
                     escapechar='\\',  # Escape special characters
                     encoding='utf-8')
        else:
            # Create new file with headers
            df.to_csv(analysis_logs_file, index=False, 
                     quoting=1,  # QUOTE_ALL - quote all fields
                     escapechar='\\',  # Escape special characters
                     encoding='utf-8')
        
    except Exception as e:
        print(f"Error logging data analysis: {str(e)}")

# Initialize session ID for new users
def initialize_session():
    """Initialize session with unique IDs for tracking"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    if 'chat_id' not in session:
        session['chat_id'] = str(uuid.uuid4())

# Legacy function for backward compatibility
    """Legacy logging function - now calls the new detailed logging"""
    user_id = current_user.email if current_user.is_authenticated else 'anonymous'
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)  # Enable CORS for all routes

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

class User(UserMixin):
    def __init__(self, id, fullname, email, is_admin=False):
        self.id = id
        self.fullname = fullname
        self.email = email
        self.is_admin = is_admin
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    users_df = get_users_df()
    user_data = users_df[users_df['email'] == user_id]
    if not user_data.empty:
        is_admin = False
        if 'is_admin' in user_data.columns:
            is_admin = str(user_data.iloc[0]['is_admin']).lower() == 'true'
        return User(user_data.iloc[0]['email'], user_data.iloc[0]['fullname'], user_data.iloc[0]['email'], is_admin)
    return None

# Import unified API settings
from API_Settings import (
    get_api_key, get_default_model, is_service_available, get_fallback_service,
    GOOGLE_API_KEY, DEFAULT_AI_SERVICE, DEFAULT_GOOGLE_MODEL, DEFAULT_OPENAI_MODEL
)
import google.generativeai as genai
from openai import OpenAI

# Configure Google AI with API key
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- User Authentication ---

def get_users_df():
    if not os.path.exists('users.csv'):
        df = pd.DataFrame(columns=['fullname', 'email', 'password'])
        df.to_csv('users.csv', index=False)
        return df
    return pd.read_csv('users.csv')

def save_users_df(df):
    df.to_csv('users.csv', index=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        action = request.form.get('action', 'login')  # 'login' or 'register'
        
        if not email or not password:
            return render_template_string(LOGIN_TEMPLATE, error="Email and password are required.")
        
        users_df = get_users_df()
        user = users_df[users_df['email'] == email]
        
        if action == 'register':
            # Registration flow
            if not fullname:
                return render_template_string(LOGIN_TEMPLATE, error="Full name is required for registration.")
            
            if not user.empty:
                return render_template_string(LOGIN_TEMPLATE, error="An account with this email already exists. Please login instead.")
            
            # Create new user
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = pd.DataFrame([[fullname, email, hashed_password]], columns=['fullname', 'email', 'password'])
            users_df = pd.concat([users_df, new_user], ignore_index=True)
            save_users_df(users_df)
            
            # Log in the new user
            user_obj = User(email, fullname, email)
            login_user(user_obj, remember=True)
            session.permanent = True
            
            # Initialize session tracking
            initialize_session()
            
            # Log successful registration
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    return render_template_string(LOGIN_TEMPLATE, show_register=True)

@app.route('/logout')
@login_required
def logout():
    # Log logout action
# --- Enhanced Logging Function ---
    user_id = current_user.email if current_user.is_authenticated else 'anonymous'
    fullname = current_user.fullname if current_user.is_authenticated else 'anonymous'

    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'fullname': fullname,
        'email': user_id, # email is user_id
        'interaction_type': interaction_type,
        'page': page,
        'action': action, # Using tool_name as action
        'details': details,
        'session_data': str(session),
        'ai_model': ai_model,
        'ai_response': ai_response
    }
    
    df = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df.to_csv(interactions_file, index=False, sep=';')
    else:
        df.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')


# Unified AI function using API_Settings
def make_ai_call(prompt, system_prompt=None, service=None, model=None, user_api_key=None):
    """
    Make AI call using unified API system - Clean, Simple, Robust
    """
    try:
        # Use default service if not specified
        if not service:
            service = DEFAULT_AI_SERVICE
        
        # Get default model for service if not specified
        if not model:
            if service == 'google':
                model = DEFAULT_GOOGLE_MODEL
            elif service == 'openai':
                model = DEFAULT_OPENAI_MODEL
            else:
                model = get_default_model(service)
        
        # Get API key with proper fallback
        api_key = get_api_key(service, user_api_key)
        if not api_key:
            raise Exception(f"No API key available for {service}. Please check API_Settings.py")
        
        print(f"Using AI service: {service}, model: {model}, key available: {bool(api_key)}")
        
        if service == 'google':
            # Configure Google AI with fresh key
            genai.configure(api_key=api_key)
            
            model_instance = genai.GenerativeModel(model)
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            response = model_instance.generate_content(full_prompt)
            return response.text, model
            
        elif service == 'openai':
            # Create OpenAI client
            client = OpenAI(api_key=api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content, model
        else:
            raise Exception(f"Unsupported AI service: {service}")
            
    except Exception as e:
        error_msg = f"AI Call Error ({service}/{model}): {str(e)}"
        print(error_msg)
        
        # Try fallback service if primary fails and no user key specified
        if not user_api_key:
            if service != 'google' and is_service_available('google'):
                print(f"Trying fallback to Google AI...")
                try:
                    return make_ai_call(prompt, system_prompt, 'google', None, None)
                except:
                    pass
            elif service != 'openai' and is_service_available('openai'):
                print(f"Trying fallback to OpenAI...")
                try:
                    return make_ai_call(prompt, system_prompt, 'openai', None, None)
                except:
                    pass
        
        raise Exception(error_msg)

# --- Helper: Admin Auth Decorator ---
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Admin-Token')
        if token != ADMIN_TOKEN:
            abort(403, description='Forbidden: Invalid admin token')
        return f(*args, **kwargs)
    return decorated

def require_true_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403, description='Forbidden: Admins only')
        return f(*args, **kwargs)
    return decorated

# --- Test Endpoint ---
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend is running!'})

# --- Serve HTML files ---
@app.route('/')
def index():
    return send_file('login.html')

@app.route('/index.html')
@login_required
def traditional_form():
    return send_file('index.html')

@app.route('/admin.html')
@login_required
@require_true_admin
def admin():
    return send_file('admin.html')

@app.route('/test-connection.html')
@login_required
def test_connection():
    return send_file('test-connection.html')

@app.route('/chat.html')
@login_required
def chat():
    return send_file('chat.html')

@app.route('/story-form.html')
@login_required
def story_form():
    return send_file('story-form.html')

@app.route('/prompt-helper.html')
@login_required
def prompt_helper():
    return send_file('prompt-helper.html')

@app.route('/data-analyzer.html')
@login_required
def data_analyzer():
    return send_file('data-analyzer.html')

@app.route('/main-menu.html')
@login_required
def main_menu():
    return send_file('main-menu.html')

@app.route('/bias-research-platform.html')
@login_required
def bias_research_platform():
    return send_file('bias-research-platform.html')

@app.route('/chatbot-config.html')
@login_required
def chatbot_config():
    return send_file('chatbot-config.html')

@app.route('/chatbot-interface.html')
@login_required
def chatbot_interface():
    return send_file('chatbot-interface.html')

@app.route('/user-settings.html')
@login_required
def user_settings():
    return send_file('user-settings.html')

@app.route('/analytics.html')
@login_required
def analytics():
    return send_file('analytics.html')

@app.route('/logs.html')
@login_required
@require_true_admin
def logs():
    return send_file('logs.html')

# --- Endpoint: Get User Settings ---
@app.route('/api/user-settings', methods=['GET'])
@login_required
def get_user_settings():
    """Get current user's AI settings"""
    try:
        # Load user settings from CSV
        settings_file = 'user_settings.csv'
        if os.path.exists(settings_file):
            settings_df = pd.read_csv(settings_file)
            user_settings = settings_df[settings_df['user_id'] == current_user.email]
            
            if not user_settings.empty:
                settings = user_settings.iloc[0].to_dict()
                # Remove user_id from response
                settings.pop('user_id', None)
                return jsonify({'success': True, 'settings': settings})
        
        # Return default settings if none found
        default_settings = {
            'ai_service': DEFAULT_AI_SERVICE,
            'ai_model': DEFAULT_OPENAI_MODEL if DEFAULT_AI_SERVICE == 'openai' else DEFAULT_GOOGLE_MODEL,
            'use_custom_keys': False,
            'openai_key': '',
            'google_key': '',
            'default_audience': 'graduate',
            'show_debug': False,
            'auto_save': True
        }
        return jsonify({'success': True, 'settings': default_settings})
        
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading settings'}), 500

# --- Endpoint: Save User Settings ---
@app.route('/api/user-settings', methods=['POST'])
@login_required
def save_user_settings():
    """Save user's AI settings"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Prepare settings data
        settings_data = {
            'user_id': current_user.email,
            'ai_service': data.get('ai_service', DEFAULT_AI_SERVICE),
            'ai_model': data.get('ai_model', DEFAULT_OPENAI_MODEL if DEFAULT_AI_SERVICE == 'openai' else DEFAULT_GOOGLE_MODEL),
            'use_custom_keys': data.get('use_custom_keys', False),
            'openai_key': data.get('openai_key', ''),
            'google_key': data.get('google_key', ''),
            'default_audience': data.get('default_audience', 'graduate'),
            'show_debug': data.get('show_debug', False),
            'auto_save': data.get('auto_save', True),
            'last_updated': pd.Timestamp.now().isoformat()
        }
        
        # Save to CSV
        settings_file = 'user_settings.csv'
        settings_df = pd.DataFrame([settings_data])
        
        if os.path.exists(settings_file):
            # Update existing user settings or add new ones
            existing_df = pd.read_csv(settings_file)
            existing_df = existing_df[existing_df['user_id'] != current_user.email]
            settings_df = pd.concat([existing_df, settings_df], ignore_index=True)
        
        settings_df.to_csv(settings_file, index=False)
        
        # Log the action
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        print(f"Error saving user settings: {str(e)}")
        return jsonify({'success': False, 'message': 'Error saving settings'}), 500

# --- Endpoint: Get User Information ---
@app.route('/api/user-info', methods=['GET'])
def get_user_info():
    """Get current user information"""
    if current_user.is_authenticated:
        return jsonify({
            'user': {
                'id': current_user.id,
                'fullname': current_user.fullname,
                'email': current_user.email
            },
            'authenticated': True
        })
    else:
        return jsonify({'authenticated': False}), 401

# --- Endpoint: Get Field Explanations ---
@app.route('/api/field-help/<field_name>', methods=['GET'])
def get_field_help(field_name):
    """Get explanation and example for a specific field"""
    explanation = get_field_explanation(field_name)
    return jsonify(explanation)

# --- Endpoint: Get Random Sample Data ---
@app.route('/api/sample-data/<field_name>', methods=['GET'])
def get_sample_data(field_name):
    """Get random sample data for a specific field"""
    sample = get_random_example(field_name)
    return jsonify({'sample': sample})

# --- Endpoint: Get Configuration Info ---
@app.route('/api/config', methods=['GET'])
def get_config_info():
    """Get current configuration information (legacy endpoint)"""
    config = get_ai_config()
    # Legacy format for backward compatibility
    legacy_config = {
        'service': config['default_service'],
        'google_key_available': config['system_google_key_available'],
        'openai_key_available': config['system_openai_key_available']
    }
    return jsonify(legacy_config)

# --- Endpoint: Get AI Configuration ---
@app.route('/api/ai-config', methods=['GET'])
def get_ai_configuration():
    """Get comprehensive AI configuration for model selection"""
    from config import get_ai_configuration
    config = get_ai_configuration()
    return jsonify(config)

# --- Endpoint: Auto-fill Form with Sample Data ---
@app.route('/api/auto-fill', methods=['GET'])
def auto_fill_form():
    """Generate a complete form filled with logically consistent sample data"""
    import random
    
    # Define positive and negative behaviors for logical consistency
    positive_behaviors = [
        'is highly conscientious consistently demonstrating organization and self-discipline in their studies',
        'shows a high need for cognition actively engaging in complex problem-solving and effortful thinking',
        'has strong performance self-efficacy believing in their ability to succeed in specific academic tasks',
        'is intrinsically motivated learning for the inherent satisfaction and interest in the subject matter',
        'exhibits excellent effort regulation persisting with difficult or uninteresting academic tasks',
        'effectively uses time and study management strategies to plan and allocate their learning activities',
        'demonstrates strong metacognitive skills by planning monitoring and evaluating their own learning processes',
        'proactively seeks help from instructors and peers when encountering difficulties',
        'employs a deep approach to learning focusing on understanding the meaning and connections between concepts',
        'feels a strong sense of academic and social integration within the university community'
    ]
    
    negative_behaviors = [
        'consistently procrastinates delaying the start and completion of academic tasks',
        'is motivated by an avoidance goal orientation focusing more on not failing than on achieving success',
        'experiences high levels of test anxiety which negatively impacts their exam performance',
        'utilizes a surface approach to learning memorizing information just enough to pass without deeper understanding',
        'is under a high degree of academic stress due to coursework and deadlines',
        'has a high level of extraversion that appears to negatively correlate with performance possibly due to prioritizing social activities',
        'exhibits symptoms of depression which is impacting their academic outcomes',
        'struggles with general life stress which spills over and affects their academic work',
        'lacks effective self-regulatory strategies leading to disorganized study habits',
        'avoids challenging tasks and gives up easily when faced with academic difficulty'
    ]
    
    positive_analytics = [
        'a consistent pattern of submitting assignments well before the deadline which is often coupled with early and regular access to the associated learning resources',
        'a pattern of watching instructional videos to completion and contributing insightful well-structured posts in discussion forums that build upon and extend course concepts',
        'consistently high scores on exams and quizzes often achieved with minimal attempts which signals a strong and confident grasp of the course material',
        'frequent logins throughout the week at regular times resulting in a high overall time-on-site and a sustained active presence in the course environment',
        'data showing significant time spent on challenging tasks and a high course completion rate indicating the student is on track and applying themselves diligently',
        'a logical sequence of activity within the learning management system such as reviewing lecture notes and optional readings before attempting related assessments',
        'active central participation in group projects supported by positive peer assessment ratings from teammates'
    ]
    
    negative_analytics = [
        'a recurring pattern of submitting assignments at the last minute which is directly preceded by intense short bursts of platform activity after long periods of inactivity',
        'consistently low or failing scores on exams and quizzes often coupled with multiple failed attempts signaling a poor understanding of core concepts',
        'a pattern of skipping through instructional videos or watching less than a quarter of them combined with discussion posts that are short off-topic or add no value',
        'infrequent logins a very low overall time-on-site and a general lack of digital presence in the learning environment',
        'minimal time spent on tasks avoidance of challenging modules and a stalled course completion rate with many overdue items'
    ]
    
    positive_decisions = [
        'advanced enrichment opportunities', 'research collaboration opportunities', 'independent study options',
        'maintain current support level', 'peer mentorship opportunities', 'advanced project opportunities',
        'independent research track', 'collaborative learning enhancement', 'thesis research support',
        'peer mentorship program', 'accelerated coursework', 'honors program admission',
        'research assistant position', 'dissertation fellowship', 'lab research opportunity',
        'teaching assistant role', 'coding bootcamp advancement', 'clinical placement priority',
        'conference presentation opportunity', 'student leadership role', 'MBA honors track',
        'engineering competition team', 'medical residency preparation', 'creative writing workshop',
        'undergraduate research grant'
    ]
    
    negative_decisions = [
        'intensive academic support', 'remedial coursework', 'anxiety management support',
        'study skills training', 'stress management program', 'time management counseling',
        'mental health support services', 'holistic wellness program', 'study skills workshop',
        'academic resilience training', 'procrastination intervention', 'confidence building program',
        'test preparation support', 'deep learning strategies', 'stress reduction techniques',
        'academic focus training', 'counseling and academic support'
    ]
    
    # Decide if this will be a positive or negative scenario
    is_positive_scenario = random.choice([True, False])
    
    if is_positive_scenario:
        # Positive scenario: good behavior -> good analytics -> good outcomes
        behavior = random.choice(positive_behaviors)
        analytics = random.choice(positive_analytics)
        progress = 'well'
        support_hours = random.randint(1, 3)  # Less support needed
        support_decision = random.choice(positive_decisions)
        support_result = random.randint(85, 100)  # High scores
        completion_status = 'completed'
    else:
        # Negative scenario: poor behavior -> poor analytics -> poor outcomes
        behavior = random.choice(negative_behaviors)
        analytics = random.choice(negative_analytics)
        progress = 'poorly'
        support_hours = random.randint(4, 8)  # More support needed
        support_decision = random.choice(negative_decisions)
        support_result = random.randint(45, 75)  # Lower scores
        completion_status = random.choice(['dropped out of', 'continued with'])
    
    # Generate consistent form data
    form_data = {
        'Nationality': random.choice(['German', 'American', 'Chinese', 'Indian', 'British', 'Canadian', 'Australian', 'French', 'Spanish', 'Brazilian']),
        'Pronoun': random.choice(['his', 'her', 'their']),
        'Student_State_Trait_Behaviour': behavior,
        'Degree_Level': random.choice(['K12 School', 'Bachelor\'s Degree', 'Master\'s Degree', 'Doctoral Degree']),
        'Field_of_Study': random.choice(['Computer Science', 'Psychology', 'Mathematics', 'Nursing', 'Business Administration', 'Engineering', 'Chemistry', 'Medicine', 'Physics', 'Sociology', 'Literature', 'Philosophy', 'Environmental Science', 'History', 'Biology']),
        'Progress_Descriptor': progress,
        'Learning_Analytics': analytics,
        'Support_Hours': support_hours,
        'Support_Period': random.choice(['Per Week', 'Per Month']),
        'Support_Delivery_Method': random.choice(['By the teacher', 'At home (self-directed)', 'By a senior peer']),
        'Support_Decision': support_decision,
        'Support_Duration': random.choice(['One semester', 'Six weeks', 'Two months', 'One month', 'Other']),
        'Support_Result': support_result,
        'Completion_Status': completion_status
    }
    
    return jsonify(form_data)

# --- Endpoint: Log User Interaction ---
@app.route('/api/log-interaction', methods=['POST'])
def log_interaction_endpoint():
    """Log user interactions to CSV"""
    data = request.json
    user_id = current_user.email if current_user.is_authenticated else 'anonymous'
    
    # Log detailed user interaction
# --- Endpoint: Log Chat Interaction ---
@app.route('/api/log-chat', methods=['POST'])
def log_chat_endpoint():
    """Log chat interactions to CSV"""
    data = request.json
    user_id = current_user.email if current_user.is_authenticated else 'anonymous'
    
    # Log chat interaction
    log_chat_interaction(
        user_id=user_id,
        chat_type=data.get('chat_type', ''),
        message_type=data.get('message_type', ''),
        content=data.get('content', ''),
        context_data=data.get('context_data'),
        ai_model=data.get('ai_model'),
        ai_response=data.get('ai_response'),
        processing_time=data.get('processing_time')
    )
    
    return jsonify({'status': 'success', 'message': 'Chat logged'})

# --- Endpoint: Get User Interactions ---
@app.route('/api/user-interactions', methods=['GET'])
@require_true_admin
def get_user_interactions():
    """Get user interaction logs"""
    try:
        interactions_file = 'user_interactions_detailed.csv'
        if os.path.exists(interactions_file):
            df = pd.read_csv(interactions_file)
            # Convert to list of dictionaries
            interactions = df.to_dict('records')
            return jsonify({'success': True, 'interactions': interactions})
        else:
            return jsonify({'success': True, 'interactions': []})
    except Exception as e:
        print(f"Error loading user interactions: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading user interactions'}), 500

# --- Endpoint: Get Chat Logs ---
@app.route('/api/chat-logs', methods=['GET'])
@require_true_admin
def get_chat_logs():
    """Get chat logs"""
    try:
        chat_logs_file = 'chat_logs_exhaustive.csv'
        if os.path.exists(chat_logs_file):
            # Read CSV with proper encoding and quoting
            df = pd.read_csv(chat_logs_file, 
                           quoting=1,  # QUOTE_ALL
                           escapechar='\\',
                           encoding='utf-8')
            # Convert to list of dictionaries
            chats = df.to_dict('records')
            return jsonify({'success': True, 'chats': chats})
        else:
            return jsonify({'success': True, 'chats': []})
    except Exception as e:
        print(f"Error loading chat logs: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading chat logs'}), 500

# --- Endpoint: Get Data Analysis Logs ---
@app.route('/api/data-analysis-logs', methods=['GET'])
@require_true_admin
def get_data_analysis_logs():
    """Get data analysis logs"""
    try:
        analysis_logs_file = 'data_analysis_logs.csv'
        if os.path.exists(analysis_logs_file):
            # Read CSV with proper encoding and quoting
            df = pd.read_csv(analysis_logs_file, 
                           quoting=1,  # QUOTE_ALL
                           escapechar='\\',
                           encoding='utf-8')
            # Convert to list of dictionaries
            analyses = df.to_dict('records')
            return jsonify({'success': True, 'analyses': analyses})
        else:
            return jsonify({'success': True, 'analyses': []})
    except Exception as e:
        print(f"Error loading data analysis logs: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading data analysis logs'}), 500

# --- Endpoint: Get Logs Statistics ---
@app.route('/api/logs-statistics', methods=['GET'])
@require_true_admin
def get_logs_statistics():
    """Get statistics from logs"""
    try:
        stats = {}
        
        # User interactions stats
        interactions_file = 'user_interactions_detailed.csv'
        if os.path.exists(interactions_file):
            df = pd.read_csv(interactions_file)
            stats['total_interactions'] = len(df)
            stats['total_users'] = df['user_id'].nunique()
            stats['most_active_user'] = df['user_id'].value_counts().index[0] if len(df) > 0 else 'N/A'
        
        # Chat logs stats
        chat_logs_file = 'chat_logs_exhaustive.csv'
        if os.path.exists(chat_logs_file):
            df = pd.read_csv(chat_logs_file, 
                           quoting=1,  # QUOTE_ALL
                           escapechar='\\',
                           encoding='utf-8')
            stats['total_chats'] = len(df)
            if 'processing_time_ms' in df.columns:
                stats['avg_processing_time'] = int(df['processing_time_ms'].mean()) if len(df) > 0 else 0
        
        # Data analysis stats
        analysis_logs_file = 'data_analysis_logs.csv'
        if os.path.exists(analysis_logs_file):
            df = pd.read_csv(analysis_logs_file, 
                           quoting=1,  # QUOTE_ALL
                           escapechar='\\',
                           encoding='utf-8')
            stats['total_analyses'] = len(df)
        
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        print(f"Error loading statistics: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading statistics'}), 500

# --- Endpoint: Submit Form Data ---
@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Add timestamp and user_id if not present
    if 'ID' not in data:
        data['ID'] = int(pd.Timestamp.now().timestamp())
    
    # Save form data
    df = pd.DataFrame([data])
    
    # Use semicolon separator to match existing format
    if not os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE, index=False, sep=';')
    else:
        df.to_csv(DATA_FILE, mode='a', header=False, index=False, sep=';')
    
    return jsonify({'status': 'success', 'message': 'Data saved successfully'})

# --- Endpoint: Admin CSV Export ---
@app.route('/api/export', methods=['GET'])
@require_true_admin
def export_csv():
    if not os.path.exists(DATA_FILE):
        return jsonify({'error': 'No data available'}), 404
    return send_file(DATA_FILE, mimetype='text/csv', as_attachment=True, download_name='submissions.csv')

# --- Endpoint: AI Chat about Vignette ---
@app.route('/api/chat', methods=['POST'])
def vignette_chat():
    data = request.json
    vignette = data.get('vignette')
    user_message = data.get('message')
    
    if not vignette or not user_message:
        return jsonify({'error': 'Both vignette and message are required'}), 400
    
    # Log user input for vignette chat
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.email,
        chat_type='vignette_chat',
        message_type='user_input',
        content=user_message,
        context_data={
            'vignette_length': len(vignette),
            'vignette_sample': vignette[:200]
        }
    )
    
    try:
        # Use configured AI service for the chat
        prompt = f"""Here is the vignette we're discussing:\n        \"{vignette}\"\n        \n        Student's question/comment: {user_message}\n        \n        Please provide a helpful, educational response following the guidelines above."""
        
        result, model = make_ai_call(prompt, CHAT_SYSTEM_PROMPT)
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.email,
            chat_type='vignette_chat',
            message_type='ai_response',
            content=result,
            context_data={
                'vignette_length': len(vignette),
                'vignette_sample': vignette[:200],
                'user_question': user_message
            },
            ai_model=model,
            ai_response=result,
            processing_time=processing_time
        )
        
        return jsonify({'response': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Chat API Error: {str(e)}")  # Add logging
        # Return a fallback response instead of error
        fallback_response = f"""Thank you for your question about the vignette. I can see you're interested in discussing: \"{user_message}\"\n\nThis vignette presents an interesting academic scenario. Here are some points to consider:\n\n1. **Student Background**: The scenario involves a student with specific characteristics and circumstances.\n2. **Support Strategy**: Consider how the support approach might impact the student's success.\n3. **Outcomes**: Think about what factors might have contributed to the results.\n\nWhat specific aspect of this scenario would you like to explore further? For example:\n- The effectiveness of the support method used\n- How the student's background might influence their learning\n- Alternative approaches that could have been considered\n\nI'm here to help you think through these educational scenarios!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Student Bias Analysis (after 10+ interactions) ---
@app.route('/api/student-bias', methods=['POST'])
def student_bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    
    if not vignette:
        return jsonify({'error': 'Vignette required'}), 400
    
    # Log user input for student bias analysis
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.email,
        chat_type='student_bias_analysis',
        message_type='user_input',
        content=vignette,
        context_data={
            'vignette_length': len(vignette),
            'analysis_type': 'bias_analysis'
        }
    )
    
    try:
        # Use configured AI service for bias analysis
        prompt = f"""Vignette to analyze:\n        {vignette}\n        \n        Please provide your bias analysis following the guidelines above. This analysis is for educational purposes to help the student understand potential biases in academic scenarios."""
        
        result, model = make_ai_call(prompt, BIAS_ANALYSIS_SYSTEM_PROMPT)
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.email,
            chat_type='student_bias_analysis',
            message_type='ai_response',
            content=result,
            context_data={
                'vignette_length': len(vignette),
                'vignette_sample': vignette[:200],
                'analysis_type': 'bias_analysis'
            },
            ai_model=model,
            ai_response=result,
            processing_time=processing_time
        )
        
        return jsonify({'bias_analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Student Bias Analysis Error: {str(e)}")
        fallback_analysis = f"""I apologize, but I'm unable to perform the bias analysis at this time due to a technical issue. \n\nHowever, here are some general questions you can consider when analyzing your vignette for potential bias:\n\n1. **Gender Bias**: Does the scenario make assumptions based on gender or pronouns?\n2. **Cultural Bias**: Are there stereotypes related to nationality or cultural background?\n3. **Academic Field Bias**: Does the scenario reflect stereotypes about certain fields of study?\n4. **Performance Bias**: Are the expectations and outcomes influenced by demographic factors?\n5. **Support Bias**: Is the type of support offered influenced by student characteristics?\n\nConsider discussing these aspects with your instructor or peers for a more comprehensive analysis."""
        
        return jsonify({'bias_analysis': fallback_analysis, 'status': 'success'})

# --- Endpoint: Prompt Engineering Assistant ---
@app.route('/api/prompt-engineering', methods=['POST'])
def prompt_engineering():
    data = request.json
    user_message = data.get('message')
    question_count = data.get('question_count', 0)
    prompt_data = data.get('prompt_data', {})
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    # Log user input for prompt engineering
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.email,
        chat_type='prompt_engineering',
        message_type='user_input',
        content=user_message,
        context_data={
            'question_count': question_count,
            'prompt_data': str(prompt_data)
        }
    )
    
    try:
        # Use Google AI for prompt engineering assistance
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        
        # Load system prompt from file
        try:
            with open('prompt-helper-system-prompt.txt', 'r') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback system prompt if file not found
            system_prompt = f"""You are an expert prompt engineering assistant specializing in data generation and analysis tasks. Your job is to help users refine their AI prompts using the PCTFT Framework through a guided conversation of maximum 7 questions.\n\nPCTFT FRAMEWORK:\n- **Persona**: Who should the AI be? (data scientist, researcher, analyst, etc.)\n- **Context**: Background information and constraints\n- **Task**: Specific action to perform\n- **Format**: Output structure (CSV, JSON, specific data schema, etc.)\n- **Target**: Intended audience and use case\n\nIMPORTANT RULES:\n1. Start by analyzing their initial prompt (even if rough/incomplete)\n2. Ask ONE question at a time to refine each PCTFT element\n3. Maximum 7 questions total\n4. Be conversational, helpful, AND provide proactive feedback\n5. Comment on their choices and suggest improvements\n6. Focus on improving their existing prompt, not starting from scratch\n7. For data generation tasks, automatically suggest appropriate data schemas\n\nCurrent conversation state:\n- Question count: {question_count}\n- Current prompt data: {prompt_data}\n- User's latest message: {user_message}\n\nIf this is the first message (question_count = 0), they're sharing their initial prompt. Analyze it, provide feedback, and ask about the first missing PCTFT element.\n\nIf this is question 7 OR you have enough information for all PCTFT elements, generate the final refined prompt with data schema if applicable.\nOtherwise, ask the next logical question while providing helpful commentary and suggestions."""
        
        prompt = system_prompt.format(
            question_count=question_count,
            prompt_data=prompt_data,
            user_message=user_message
        )
        
        response = model.generate_content(prompt)
        result = response.text
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.email,
            chat_type='prompt_engineering',
            message_type='ai_response',
            content=result,
            context_data={
                'question_count': question_count,
                'prompt_data': str(prompt_data),
                'user_question': user_message,
                'system_prompt_length': len(system_prompt)
            },
            ai_model=model_name,
            ai_response=result,
            processing_time=processing_time
        )
        
        # Increment question count
        new_question_count = question_count + 1
        
        # Update prompt data based on the question number
        updated_prompt_data = prompt_data.copy()
        if question_count == 0:
            updated_prompt_data['task'] = user_message
        elif question_count == 1:
            updated_prompt_data['context'] = user_message
        elif question_count == 2:
            updated_prompt_data['audience'] = user_message
        elif question_count == 3:
            updated_prompt_data['format'] = user_message
        elif question_count == 4:
            updated_prompt_data['tone'] = user_message
        elif question_count == 5:
            updated_prompt_data['constraints'] = user_message
        elif question_count == 6:
            updated_prompt_data['examples'] = user_message
        
        # Check if we should generate final prompt
        final_prompt = None
        if new_question_count >= 7 or "final prompt" in result.lower():
            # Let AI craft the final optimized prompt
            prompt_crafting_request = f"""Based on our conversation, please craft a professional, optimized AI prompt that incorporates all the information we've discussed. \n\nHere's what we've gathered:\n- Task: {updated_prompt_data.get('task', 'Not specified')}\n- Context: {updated_prompt_data.get('context', 'Not specified')}\n- Audience: {updated_prompt_data.get('audience', 'Not specified')}\n- Format: {updated_prompt_data.get('format', 'Not specified')}\n- Tone: {updated_prompt_data.get('tone', 'Not specified')}\n- Constraints: {updated_prompt_data.get('constraints', 'Not specified')}\n- Examples/Details: {updated_prompt_data.get('examples', 'Not specified')}\n\nPlease create a single, well-crafted prompt that someone can copy and paste into any AI system to get excellent results. The prompt should be:\n1. Clear and specific\n2. Include all necessary context\n3. Specify the desired output format\n4. Include any important constraints\n5. Be optimized for best AI performance\n\nReturn ONLY the final prompt, nothing else."""
            
            try:
                prompt_response = model.generate_content(prompt_crafting_request)
                final_prompt = prompt_response.text.strip()
            except:
                # Fallback if AI crafting fails
                final_prompt = f"Create a comprehensive {updated_prompt_data.get('task', 'response')} that addresses all the requirements we discussed in our conversation."
        
        return jsonify({
            'response': result,
            'question_count': new_question_count,
            'prompt_data': updated_prompt_data,
            'final_prompt': final_prompt,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Prompt Engineering Error: {str(e)}")
        fallback_response = f"""I apologize, but I'm having trouble processing your request right now. Let me help you with some general prompt engineering guidance:\n\nFor creating effective AI prompts, consider including:\n\n1. **Clear Task**: What exactly do you want the AI to do?\n2. **Context**: What background information is relevant?\n3. **Audience**: Who is this for?\n4. **Format**: How should the output be structured?\n5. **Tone**: What style or voice should be used?\n6. **Constraints**: Any specific requirements or limitations?\n7. **Examples**: Any specific examples to guide the AI?\n\nPlease try again, and I'll do my best to help you create an amazing prompt!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Prompt Discussion ---
@app.route('/api/prompt-discussion', methods=['POST'])
def prompt_discussion():
    data = request.json
    user_message = data.get('message')
    current_prompt = data.get('current_prompt')
    
    if not user_message or not current_prompt:
        return jsonify({'error': 'Message and current prompt required'}), 400
    
    # Log user input for prompt discussion
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.email,
        chat_type='prompt_discussion',
        message_type='user_input',
        content=user_message,
        context_data={
            'current_prompt_length': len(current_prompt),
            'current_prompt_sample': current_prompt[:200]
        }
    )
    
    try:
        # Use Google AI for prompt discussion
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        
        # Create system prompt for prompt discussion
        discussion_prompt = f"""You are an expert prompt engineering consultant. A user has created a prompt and wants to discuss it with you. Your job is to help them refine, understand, or modify their prompt based on their questions or requests.\n\nCURRENT PROMPT:\n{current_prompt}\n\nUSER'S MESSAGE/QUESTION:\n{user_message}\n\nINSTRUCTIONS:\n1. Analyze their question/request carefully\n2. Provide helpful, specific advice about their prompt\n3. If they ask for modifications, suggest specific changes\n4. If they want explanations, explain the reasoning behind prompt elements\n5. If they want alternatives, suggest different approaches\n6. Be conversational and educational\n7. If you suggest a modified prompt, provide the complete new version\n\nIMPORTANT: If you provide a modified/updated prompt, clearly indicate it as "UPDATED PROMPT:" followed by the complete new prompt text.\n\nRespond helpfully to their question about the prompt."""
        
        response = model.generate_content(discussion_prompt)
        result = response.text
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.email,
            chat_type='prompt_discussion',
            message_type='ai_response',
            content=result,
            context_data={
                'current_prompt_length': len(current_prompt),
                'current_prompt_sample': current_prompt[:200],
                'user_question': user_message,
                'discussion_prompt_length': len(discussion_prompt)
            },
            ai_model=model_name,
            ai_response=result,
            processing_time=processing_time
        )
        
        # Check if there's an updated prompt in the response
        updated_prompt = None
        if "UPDATED PROMPT:" in result:
            # Extract the updated prompt
            parts = result.split("UPDATED PROMPT:")
            if len(parts) > 1:
                updated_prompt = parts[1].strip()
                # Remove the updated prompt from the main response to avoid duplication
                result = parts[0].strip()
        
        response_data = {
            'response': result,
            'status': 'success'
        }
        
        if updated_prompt:
            response_data['updated_prompt'] = updated_prompt
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Prompt Discussion Error: {str(e)}")
        fallback_response = f"""I apologize, but I'm having trouble processing your request right now. Here are some general tips for prompt discussion:\n\n**Common Questions About Prompts:**\n- **"Make it shorter"** - I can help condense your prompt while keeping key elements\n- **"Make it more specific""** - I can add more detailed instructions and constraints\n- **"Explain why you included X""** - I can explain the reasoning behind specific prompt elements\n- **"How would this work with different AI systems?""** - I can suggest adaptations for different platforms\n- **"What if I want different output?""** - I can modify the format or style requirements\n\nPlease try your question again, and I'll do my best to help you improve your prompt!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Data Analysis ---
@app.route('/api/analyze-data', methods=['POST'])
def analyze_data():
    data = request.json
    data_content = data.get('data')
    data_type = data.get('data_type', 'text')
    
    if not data_content:
        return jsonify({'error': 'Data content required'}), 400
    
    # Log user input for data analysis
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.email,
        chat_type='data_analysis',
        message_type='user_input',
        content=data_content,
        context_data={
            'data_type': data_type,
            'data_length': len(data_content)
        }
    )
    
    try:
        # Use Google AI for data analysis
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        
        # Create analysis prompt based on data type
        if data_type == 'image':
            analysis_prompt = f"""You are an educational researcher analyzing visual data. Please provide a focused, short analysis of this image from an educational research perspective.\n\nFocus on:\n- What the image shows (content description)\n- Educational relevance or implications\n- Key patterns or insights visible\n- Research applications or potential uses\n\nKeep your analysis concise (2-3 paragraphs maximum) and educational in nature.\n\nImage data: {data_content}"""
        
        elif data_type == 'csv':
            analysis_prompt = f"""You are an educational researcher analyzing CSV data. Please provide a focused, short analysis of this dataset from an educational research perspective.\n\nFocus on:\n- Data structure and variables\n- Key patterns, trends, or outliers\n- Statistical insights (means, distributions, correlations)\n- Educational implications\n- Potential research questions this data could answer\n\nKeep your analysis concise (2-3 paragraphs maximum) and educational in nature.\n\nCSV Data:\n{data_content}"""
        
        elif data_type == 'json':
            analysis_prompt = f"""You are an educational researcher analyzing JSON data. Please provide a focused, short analysis of this dataset from an educational research perspective.\n\nFocus on:\n- Data structure and key fields\n- Patterns in the data\n- Educational insights or implications\n- Potential research applications\n\nKeep your analysis concise (2-3 paragraphs maximum) and educational in nature.\n\nJSON Data:\n{data_content}"""
        
        else:  # text or other
            analysis_prompt = f"""You are an educational researcher analyzing text data. Please provide a focused, short analysis of this content from an educational research perspective.\n\nFocus on:\n- Main themes or topics\n- Educational relevance\n- Key insights or patterns\n- Research implications\n- Potential applications in educational settings\n\nKeep your analysis concise (2-3 paragraphs maximum) and educational in nature.\n\nText Data:\n{data_content}"""
        
        response = model.generate_content(analysis_prompt)
        result = response.text
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.email,
            chat_type='data_analysis',
            message_type='ai_response',
            content=result,
            context_data={
                'data_type': data_type,
                'input_data_sample': data_content[:500],
                'analysis_prompt_length': len(analysis_prompt)
            },
            ai_model=model_name,
            ai_response=result,
            processing_time=processing_time
        )
        
        return jsonify({'analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Data Analysis Error: {str(e)}")
        
        # Provide fallback analysis based on data type
        if data_type == 'csv':
            fallback_analysis = f"""I apologize, but I'm having trouble analyzing your CSV data right now. Here's some general guidance for CSV data analysis:\n\n**Key Areas to Examine:**\n- **Data Quality**: Check for missing values, outliers, or inconsistencies\n- **Descriptive Statistics**: Calculate means, medians, standard deviations for numerical columns\n- **Patterns**: Look for trends, correlations between variables, or groupings\n- **Educational Insights**: Consider how this data relates to learning outcomes, student performance, or educational interventions\n\nFor a more detailed analysis, try uploading a smaller sample or checking the data format."""
        
        elif data_type == 'image':
            fallback_analysis = f"""I apologize, but I'm having trouble analyzing your image right now. Here's some general guidance for image analysis in educational research:\n\n**Key Areas to Consider:**\n- **Content Analysis**: What educational materials, settings, or activities are shown?\n- **Visual Elements**: Charts, graphs, text, or educational tools visible\n- **Context**: Classroom environment, learning materials, or student work\n- **Research Applications**: How this visual data could support educational research\n\nPlease try uploading a smaller image file or a different format."""
        
        else:
            fallback_analysis = f"""I apologize, but I'm having trouble analyzing your data right now. Here's some general guidance for data analysis in educational research:\n\n**Key Areas to Examine:**\n- **Content Themes**: What are the main topics or concepts?\n- **Patterns**: Are there recurring elements or trends?\n- **Educational Relevance**: How does this relate to learning, teaching, or educational outcomes?\n- **Research Potential**: What questions could this data help answer?\n\nPlease try with a smaller data sample or check the format."""
        
        return jsonify({'analysis': fallback_analysis, 'status': 'success'})

# --- Endpoint: Data Interpretation ---
@app.route('/api/interpret-data', methods=['POST'])
@login_required
def interpret_data():
    data = request.json
    data_content = data.get('data')
    data_type = data.get('data_type', 'text')
    research_context = data.get('research_context', '')
    analysis_type = data.get('analysis_type', '')
    target_insights = data.get('target_insights', '')
    audience_level = data.get('audience_level', 'undergraduate')
    
    # Get AI settings from request
    ai_service = data.get('ai_service')
    ai_model = data.get('ai_model')
    use_custom_keys = data.get('use_custom_keys', False)
    user_openai_key = data.get('openai_key', '')
    user_google_key = data.get('google_key', '')
    
    # Determine which API key to use
    user_api_key = None
    if use_custom_keys:
        if ai_service == 'openai' and user_openai_key:
            user_api_key = user_openai_key
        elif ai_service == 'google' and user_google_key:
            user_api_key = user_google_key
    
    if not data_content:
        return jsonify({'error': 'Data content required'}), 400
    
    # Log user input for data interpretation
    start_time = time.time()
    user_email = current_user.email if current_user.is_authenticated else 'anonymous'
# --- Endpoint: Interactive Data Interpretation Chat ---
@app.route('/api/interpret-chat', methods=['POST'])
@login_required
def interpret_chat():
    data = request.json
    user_message = data.get('message')
    current_analysis = data.get('current_analysis')
    research_context = data.get('research_context', '')
    analysis_type = data.get('analysis_type', '')
    target_insights = data.get('target_insights', '')
    audience_level = data.get('audience_level', 'undergraduate')
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    # Log user chat message
    start_time = time.time()
    user_email = current_user.email if current_user.is_authenticated else 'anonymous'
    log_chat_interaction(
        user_id=user_email,
        chat_type='data_interpreter_chat',
        message_type='user_input',
        content=user_message,
        context_data={
            'research_context': research_context,
            'analysis_type': analysis_type,
            'target_insights': target_insights,
            'audience_level': audience_level,
            'current_analysis_length': len(current_analysis) if current_analysis else 0
        }
    )
    
    try:
        # Create chat prompt for data interpretation discussion
        chat_prompt = f"""You are an expert data interpreter engaged in an interactive discussion about a statistical analysis. Your role is to help the user understand, refine, and explore their data interpretation through conversation.\n\nCURRENT ANALYSIS CONTEXT:\nResearch Context: {research_context if research_context else 'General educational research'}\nAnalysis Type: {analysis_type if analysis_type else 'General statistical analysis'}\nTarget Insights: {target_insights if target_insights else 'General interpretation'}\nAudience Level: {audience_level}\n\nCURRENT ANALYSIS:\n{current_analysis if current_analysis else 'No analysis provided yet'}\n\nUSER'S QUESTION/REQUEST:\n{user_message}\n\nINSTRUCTIONS:\n1. Respond to the user's specific question or request about the analysis\n2. Provide educational explanations appropriate for their audience level\n3. If they ask for clarifications, explain statistical concepts clearly\n4. If they want to explore implications, discuss practical applications\n5. If they request modifications to the analysis, provide an updated interpretation\n6. Be conversational, helpful, and educational\n7. Encourage critical thinking about the results\n\nIMPORTANT: If you provide a significantly updated or refined analysis based on their request, clearly indicate it as "UPDATED ANALYSIS:" followed by the complete new interpretation."""
        
        result, model = make_ai_call(chat_prompt)
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI chat response
        log_chat_interaction(
            user_id=user_email,
            chat_type='data_interpreter_chat',
            message_type='ai_response',
            content=result,
            context_data={
                'research_context': research_context,
                'analysis_type': analysis_type,
                'target_insights': target_insights,
                'audience_level': audience_level,
                'user_question': user_message,
                'current_analysis_sample': current_analysis[:500] if current_analysis else None
            },
            ai_model=model,
            ai_response=result,
            processing_time=processing_time
        )
        
        # Check if there's an updated analysis in the response
        updated_analysis = None
        if "UPDATED ANALYSIS:" in result:
            # Extract the updated analysis
            parts = result.split("UPDATED ANALYSIS:")
            if len(parts) > 1:
                updated_analysis = parts[1].strip()
                # Remove the updated analysis from the main response to avoid duplication
                result = parts[0].strip()
        
        response_data = {
            'response': result,
            'status': 'success'
        }
        
        if updated_analysis:
            response_data['updated_analysis'] = updated_analysis
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Interpretation Chat Error: {str(e)}")
        fallback_response = f"""I apologize, but I'm having trouble processing your question right now. Here are some ways I can help you discuss your data interpretation:\n\n**Common Discussion Topics:**\n- **\"What does this p-value mean?\"** - I can explain statistical significance in practical terms\n- **\"Is this effect size meaningful?\"** - I can discuss practical vs statistical significance\n- **\"What are the limitations?\"** - I can help identify potential issues with the analysis\n- **\"How do I explain this to others?\"** - I can help you communicate results clearly\n- **\"What should I do next?\"** - I can suggest follow-up analyses or actions\n\nPlease try your question again, and I'll do my best to help you understand and refine your data interpretation!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Educational Chatbot ---
@app.route('/api/educational-chat', methods=['POST'])
@login_required
def educational_chat():
    data = request.json
    user_message = data.get('message')
    system_prompt = data.get('system_prompt')
    chat_history = data.get('chat_history', [])
    config = data.get('config', {})
    
    # Get AI service info if custom
    ai_service = data.get('ai_service')
    use_custom_keys = data.get('use_custom_keys', False)
    user_openai_key = data.get('openai_key', '')
    user_google_key = data.get('google_key', '')
    
    # Determine which API key to use
    user_api_key = None
    if use_custom_keys:
        if ai_service == 'openai' and user_openai_key:
            user_api_key = user_openai_key
        elif ai_service == 'google' and user_google_key:
            user_api_key = user_google_key
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    if not system_prompt:
        return jsonify({'error': 'System prompt required'}), 400
    
    # Log user chat message
    start_time = time.time()
    user_email = current_user.email if current_user.is_authenticated else 'anonymous'
    log_chat_interaction(
        user_id=user_email,
        chat_type='educational_chat',
        message_type='user_input',
        content=user_message,
        context_data={
            'system_prompt_length': len(system_prompt) if system_prompt else 0,
            'chat_history_length': len(chat_history),
            'config': str(config),
            'ai_service': ai_service,
            'use_custom_keys': use_custom_keys
        }
    )
    
    try:
        # Determine AI service and model
        if config.get('modelType') == 'custom' and ai_service and user_api_key:
            # Use custom AI service
            service = ai_service
            api_key = user_api_key
            # Use default model for the service
            model = DEFAULT_OPENAI_MODEL if service == 'openai' else DEFAULT_GOOGLE_MODEL
        else:
            # Use system default
            service = DEFAULT_AI_SERVICE
            api_key = None
            model = DEFAULT_OPENAI_MODEL if service == 'openai' else DEFAULT_GOOGLE_MODEL
        
        # Create conversation context from chat history
        conversation_context = ""
        if chat_history:
            recent_history = chat_history[-6:]  # Last 6 messages for context
            for msg in recent_history:
                if msg.get('type') == 'user':
                    conversation_context += f"Student: {msg.get('content', '')}\n"
                elif msg.get('type') == 'bot':
                    conversation_context += f"Assistant: {msg.get('content', '')}\n"
        
        # Create full prompt with context
        full_prompt = f"""Previous conversation:\n{conversation_context}\n\nCurrent student message: {user_message}\n\nPlease respond as the educational assistant following your persona and guidelines."""
        
        # Make AI call
        result, model = make_ai_call(
            full_prompt,
            system_prompt,
            service=service,
            model=model,
            user_api_key=user_api_key
        )
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI chat response
        log_chat_interaction(
            user_id=user_email,
            chat_type='educational_chat',
            message_type='ai_response',
            content=result,
            context_data={
                'system_prompt_sample': system_prompt[:200] if system_prompt else None,
                'chat_history_length': len(chat_history),
                'config': str(config),
                'ai_service': ai_service,
                'use_custom_keys': use_custom_keys,
                'user_question': user_message,
                'conversation_context_length': len(conversation_context)
            },
            ai_model=model,
            ai_response=result,
            processing_time=processing_time
        )
        
        return jsonify({'response': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Educational Chat Error: {str(e)}")
        
        # Provide educational fallback response
        fallback_response = f"""I understand you're asking about: \"{user_message}\"\n\nI apologize, but I'm having a technical difficulty right now. However, I'd still like to help you learn! Here are some ways we can approach your question:\n\n1. **Break it down**: Can you tell me what specific part you'd like to understand better?\n2. **Context**: What have you already learned about this topic?\n3. **Application**: How do you think this might be used in real situations?\n\nPlease try asking your question again, and I'll do my best to help you understand the concept step by step!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: AI Bias Analysis ---
@app.route('/api/bias', methods=['POST'])
@require_true_admin
def bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    api_key = data.get('api_key')
    service = data.get('service', AI_SERVICE)
    
    # Only return mock for explicit test requests
    if api_key == 'test' or api_key == 'TEST':
        # Return mock analysis for testing
        mock_analysis = f"""MOCK BIAS ANALYSIS:\n        \n        Vignette analyzed: \"{vignette[:100]}{'...' if len(vignette) > 100 else ''}\"\n\nPotential bias indicators found:\n- Gender representation: Check pronoun usage\n- Nationality bias: Review nationality selection\n- Academic field stereotypes: Examine field of study choices\n- Performance assumptions: Analyze progress descriptors\n\nRecommendation: This is a test response. For real bias analysis, provide a valid API key."""
        
        return jsonify({'bias_analysis': mock_analysis})
    
    if not vignette:
        return jsonify({'error': 'Vignette required'}), 400
    
    try:
        if service == 'google' or not api_key:
            # Use Google AI (embedded API key)
            model_name = 'gemini-pro'
            model = genai.GenerativeModel(model_name)
            prompt = f"""{BIAS_ANALYSIS_SYSTEM_PROMPT}\n            \nVignette to analyze:\n{vignette}\n            \nPlease provide your bias analysis following the guidelines above."""
            
            response = model.generate_content(prompt)
            result = response.text
            return jsonify({'bias_analysis': result, 'service': 'google'})
            
        elif service == 'openai':
            # Use OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "system", "content": "You are an expert in bias detection for academic vignettes."},
                    {"role": "user", "content": f"Analyze the following vignette for bias and provide a brief explanation: {vignette}"}
                ]
            )
            result = response.choices[0].message.content
            return jsonify({'bias_analysis': result, 'service': 'openai'})
            
        else:
            return jsonify({'error': 'Invalid service specified'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

SYSTEM_SETTINGS_FILE = 'system_settings.csv'
SYSTEM_SETTINGS_FIELDS = ['ai_service', 'aio_model', 'openai_key', 'google_key']

def load_system_settings():
    settings = {k: '' for k in SYSTEM_SETTINGS_FIELDS}
    try:
        with open(SYSTEM_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['setting'] in settings:
                    settings[row['setting']] = row['value']
    except Exception:
        pass
    return settings

def save_system_settings(new_settings):
    # Read current settings
    settings = load_system_settings()
    # Update with new values
    for k in SYSTEM_SETTINGS_FIELDS:
        if k in new_settings:
            settings[k] = new_settings[k]
    # Write back to CSV
    with open(SYSTEM_SETTINGS_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['setting', 'value'])
        for k in SYSTEM_SETTINGS_FIELDS:
            writer.writerow([k, settings[k]])

# --- Endpoint: Get System AI Settings (Admin Only) ---
@app.route('/api/system-settings', methods=['GET'])
@login_required
@require_true_admin
def get_system_settings():
    settings = load_system_settings()
    return jsonify({'success': True, 'settings': settings})

# --- Endpoint: Update System AI Settings (Admin Only) ---
@app.route('/api/system-settings', methods=['POST'])
@login_required
@require_true_admin
def update_system_settings():
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    save_system_settings(data)
    return jsonify({'success': True, 'message': 'System settings updated successfully'})

# --- Endpoints: Central Database Management (Admin) ---
@app.route('/api/admin/database-stats')
@login_required
def database_stats():
    """Get database statistics for admin interface"""
    try:
        from central_database_admin import CentralDatabase
        db = CentralDatabase()
        stats = db.get_database_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/export-chat-logs', methods=['POST'])
@login_required
def export_chat_logs():
    """Export chat logs to CSV with filtering options"""
    try:
        from central_database_admin import CentralDatabase
        
        data = request.json or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        module = data.get('module')
        user_filter = data.get('user')
        
        db = CentralDatabase()
        filename, count = db.export_chat_logs(
            date_from=date_from,
            date_to=date_to,
            module=module,
            user_email=user_filter
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'count': count,
            'message': f'Exported {count:,} chat log entries to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/export-users', methods=['POST'])
@login_required
def export_users():
    """Export users data to CSV"""
    try:
        from central_database_admin import CentralDatabase
        
        db = CentralDatabase()
        filename, count = db.export_users_data()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'count': count,
            'message': f'Exported {count:,} users to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/export-interactions', methods=['POST'])
@login_required
def export_interactions():
    """Export user interactions to CSV"""
    try:
        from central_database_admin import CentralDatabase
        
        data = request.json or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        user_filter = data.get('user')
        
        db = CentralDatabase()
        filename, count = db.export_user_interactions(
            date_from=date_from,
            date_to=date_to,
            user_email=user_filter
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'count': count,
            'message': f'Exported {count:,} user interactions to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/export-submissions', methods=['POST'])
@login_required
def export_submissions():
    """Export user submissions to CSV"""
    try:
        from central_database_admin import CentralDatabase
        
        data = request.json or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        user_filter = data.get('user')
        
        db = CentralDatabase()
        filename, count = db.export_user_submissions(
            date_from=date_from,
            date_to=date_to,
            user_email=user_filter
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'count': count,
            'message': f'Exported {count:,} user submissions to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/download-export/<filename>')
@login_required
def download_export(filename):
    """Download exported CSV file"""
    try:
        # Security check - allow various export file patterns
        allowed_patterns = [
            'chat_logs_export_',
            'users_export_',
            'user_interactions_export_',
            'user_submissions_export_',
            'data_analysis_export_'
        ]
        
        if not any(filename.startswith(pattern) for pattern in allowed_patterns) or not filename.endswith('.csv'):
            abort(404)
        
        if not os.path.exists(filename):
            abort(404)
        
        return send_file(filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        abort(404)

# --- Endpoints: Custom Chatbot Management (Admin) ---
@app.route('/api/admin/chatbots')
@login_required
@require_true_admin
def get_chatbots():
    """Get all custom chatbots for admin management"""
    try:
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, u.fullname as created_by_name,
                   COUNT(DISTINCT conv.id) as conversation_count,
                   COUNT(DISTINCT conv.user_id) as unique_users
            FROM custom_chatbots c
            LEFT JOIN users u ON c.created_by = u.id
            LEFT JOIN chatbot_conversations conv ON c.id = conv.chatbot_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        ''')
        
        chatbots = []
        for row in cursor.fetchall():
            chatbots.append({
                'id': row[0],
                'name': row[1],
                'display_name': row[2],
                'description': row[3],
                'greeting_message': row[4],
                'system_prompt': row[5],
                'ai_service': row[6],
                'ai_model': row[7],
                'is_active': bool(row[8]),
                'created_by': row[9],
                'created_at': row[10],
                'updated_at': row[11],
                'deployment_settings': row[12],
                'usage_count': row[13],
                'created_by_name': row[14],
                'conversation_count': row[15],
                'unique_users': row[16]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'chatbots': chatbots
        })
        
    except Exception as e:
        print(f"ERROR in get_chatbots: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbot-stats')
@login_required
@require_true_admin
def get_chatbot_stats():
    """Get chatbot system statistics"""
    try:
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        # Combined stats query
        cursor.execute('''
            SELECT 
                COUNT(*) as total_chatbots,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_chatbots,
                SUM(usage_count) as total_interactions
            FROM custom_chatbots
        ''')
        
        row = cursor.fetchone()
        total_chatbots = row[0]
        active_chatbots = row[1]
        total_interactions = row[2] or 0
        
        # Total conversations
        cursor.execute("SELECT COUNT(*) FROM chatbot_conversations")
        total_conversations = cursor.fetchone()[0]
        
        # Unique users served
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM chatbot_conversations WHERE user_id IS NOT NULL")
        unique_users = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute("SELECT COUNT(*) FROM chatbot_messages")
        total_messages = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_chatbots': total_chatbots,
                'active_chatbots': active_chatbots,
                'total_conversations': total_conversations,
                'total_interactions': total_interactions,
                'total_messages': total_messages,
                'unique_users': unique_users
            }
        })
        
    except Exception as e:
        print(f"ERROR in get_chatbot_stats: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbots/create', methods=['POST'])
@login_required
@require_true_admin
def create_chatbot():
    """Create a new custom chatbot"""
    try:
        data = request.json
        
        # Get current user ID
        from central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Generate internal name from display name
        import re
        internal_name = re.sub(r'[^a-zA-Z0-9_]', '_', data['display_name'].lower())
        
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO custom_chatbots 
            (name, display_name, description, greeting_message, system_prompt, 
             ai_service, ai_model, is_active, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            internal_name, data['display_name'], data.get('description', ''),
            data['greeting_message'], data['system_prompt'],
            data.get('ai_service', 'google'), data.get('ai_model', 'gemini-1.5-flash'),
            data.get('is_active', True), user_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Chatbot "{data["display_name"]}" created successfully!'
        })
        
    except Exception as e:
        print(f"ERROR in create_chatbot: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbots/update', methods=['POST'])
@login_required
@require_true_admin
def update_chatbot():
    """Update an existing custom chatbot"""
    try:
        data = request.json
        chatbot_id = data['id']
        
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE custom_chatbots 
            SET display_name = ?, description = ?, greeting_message = ?, 
                system_prompt = ?, ai_service = ?, ai_model = ?, 
                is_active = ?, updated_at = ?
            WHERE id = ?
        ''', (
            data['display_name'], data.get('description', ''),
            data['greeting_message'], data['system_prompt'],
            data.get('ai_service', 'google'), data.get('ai_model', 'gemini-1.5-flash'),
            data.get('is_active', True), datetime.now().isoformat(), chatbot_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Chatbot "{data["display_name"]}" updated successfully!'
        })
        
    except Exception as e:
        print(f"ERROR in update_chatbot: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbots/toggle', methods=['POST'])
@login_required
@require_true_admin
def toggle_chatbot():
    """Toggle chatbot active status"""
    try:
        data = request.json
        chatbot_id = data['id']
        is_active = data['is_active']
        
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('UPDATE custom_chatbots SET is_active = ?, updated_at = ? WHERE id = ?',
                      (is_active, datetime.now().isoformat(), chatbot_id))
        
        conn.commit()
        conn.close()
        
        status = "activated" if is_active else "deactivated"
        return jsonify({
            'success': True,
            'message': f'Chatbot {status} successfully!'
        })
        
    except Exception as e:
        print(f"ERROR in toggle_chatbot: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbots/delete', methods=['POST'])
@login_required
@require_true_admin
def delete_chatbot():
    """Delete a custom chatbot"""
    try:
        data = request.json
        chatbot_id = data['id']
        
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        # Delete related data first
        cursor.execute('DELETE FROM chatbot_messages WHERE chatbot_id = ?', (chatbot_id,))
        cursor.execute('DELETE FROM chatbot_conversations WHERE chatbot_id = ?', (chatbot_id,))
        cursor.execute('DELETE FROM chatbot_analytics WHERE chatbot_id = ?', (chatbot_id,))
        cursor.execute('DELETE FROM custom_chatbots WHERE id = ?', (chatbot_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Chatbot deleted successfully!'
        })
        
    except Exception as e:
        print(f"ERROR in delete_chatbot: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# --- Endpoints: Custom Chatbot User Interface ---
@app.route('/api/chatbots/available')
@login_required
def get_available_chatbots():
    """Get all active chatbots for users"""
    try:
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, display_name, description, greeting_message
            FROM custom_chatbots 
            WHERE is_active = 1
            ORDER BY display_name
        ''')
        
        chatbots = []
        for row in cursor.fetchall():
            chatbots.append({
                'id': row[0],
                'display_name': row[1],
                'description': row[2],
                'greeting_message': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'chatbots': chatbots
        })
        
    except Exception as e:
        print(f"ERROR in get_available_chatbots: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chatbots/start-conversation', methods=['POST'])
@login_required
def start_chatbot_conversation():
    """Start a new conversation with a chatbot"""
    try:
        data = request.json
        chatbot_id = data['chatbot_id']
        
        # Get user ID
        from central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create conversation record
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chatbot_conversations 
            (chatbot_id, user_id, session_id, started_at, last_activity)
            VALUES (?, ?, ?, ?, ?)
        ''', (chatbot_id, user_id, session_id, datetime.now().isoformat(), datetime.now().isoformat()))
        
        conversation_id = cursor.lastrowid
        
        # Update usage count
        cursor.execute('UPDATE custom_chatbots SET usage_count = usage_count + 1 WHERE id = ?', (chatbot_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"ERROR in start_chatbot_conversation: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chatbots/chat', methods=['POST'])
@login_required
def chatbot_chat():
    """Send message to chatbot and get response"""
    try:
        data = request.json
        conversation_id = data['conversation_id']
        chatbot_id = data['chatbot_id']
        user_message = data['message']
        
        # Get user ID
        from central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Get chatbot configuration
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT system_prompt, ai_service, ai_model FROM custom_chatbots WHERE id = ?', (chatbot_id,))
        chatbot_config = cursor.fetchone()
        
        if not chatbot_config:
            return jsonify({'success': False, 'error': 'Chatbot not found'}), 404
        
        system_prompt, ai_service, ai_model = chatbot_config
        
        # Store user message
        cursor.execute('''
            INSERT INTO chatbot_messages 
            (conversation_id, chatbot_id, user_id, sender, message, timestamp)
            VALUES (?, ?, ?, 'user', ?, ?)
        ''', (conversation_id, chatbot_id, user_id, user_message, datetime.now().isoformat()))
        
        # Update conversation activity
        cursor.execute('''
            UPDATE chatbot_conversations 
            SET last_activity = ?, message_count = message_count + 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), conversation_id))
        
        conn.commit()
        conn.close()
        
        # Get AI response
        start_time = datetime.now()
        try:
            ai_response, model_used = make_ai_call(
                prompt=user_message,
                system_prompt=system_prompt,
                service=ai_service,
                model=ai_model
            )
        except Exception as ai_error:
            ai_response = "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
            model_used = ai_model
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Store AI response
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chatbot_messages 
            (conversation_id, chatbot_id, user_id, sender, message, ai_model, response_time_sec, timestamp)
            VALUES (?, ?, ?, 'chatbot', ?, ?, ?, ?)
        ''', (conversation_id, chatbot_id, user_id, ai_response, model_used, response_time, datetime.now().isoformat()))
        
        # Update conversation activity
        cursor.execute('''
            UPDATE chatbot_conversations 
            SET last_activity = ?, message_count = message_count + 1
            WHERE id = ?
        ''', (datetime.now().isoformat(), conversation_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'model_used': model_used,
            'response_time': response_time
        })
        
    except Exception as e:
        print(f"AI Call Error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Error in AI call: {str(e)}"}), 500

@app.route('/api/chatbots/feedback', methods=['POST'])
@login_required
def chatbot_feedback():
    """Submit feedback for a conversation"""
    try:
        data = request.json
        conversation_id = data['conversation_id']
        rating = data['rating']
        
        conn = sqlite3.connect('laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE chatbot_conversations 
            SET conversation_rating = ?
            WHERE id = ?
        ''', (rating, conversation_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully'
        })
        
    except Exception as e:
        print(f"ERROR in chatbot_feedback: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Serve Admin and User Pages ---
@app.route('/chatbot-admin.html')
@login_required
@require_true_admin
def chatbot_admin():
    return send_file('chatbot-admin.html')

@app.route('/custom-chatbots.html')
@login_required
def custom_chatbots():
    return send_file('custom-chatbots.html')

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Backend will be available at: http://localhost:5001")
    print("Test page: http://localhost:5001/test-connection.html")
    print("Admin panel: http://localhost:5001/admin.html")
    print("Chatbot admin: http://localhost:5001/chatbot-admin.html")
    app.run(debug=True, host='0.0.0.0', port=5001)