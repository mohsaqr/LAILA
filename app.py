from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory, send_file, render_template_string, abort
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import sqlite3
import openai
import google.generativeai as genai
from config import get_ai_configuration, LOGIN_TEMPLATE, ADMIN_ACCESS_DENIED_TEMPLATE, CHAT_SYSTEM_PROMPT, load_bias_analysis_prompt, load_system_prompt, list_available_prompts
from API_Settings import  DEFAULT_AI_SERVICE, DEFAULT_GOOGLE_MODEL, DEFAULT_OPENAI_MODEL, is_service_available, get_api_key
import bcrypt
import uuid
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime, timedelta
import random
import time
import traceback
import sys
import csv
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


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
        
        # Prepare data for database
        module = chat_type.replace('_chat', '').replace('_', ' ').title()
        sender = 'User' if message_type == 'user_input' else 'AI'
        turn = session.get(turn_key, 1)
        message = clean_message(content if message_type == 'user_input' else ai_response)
        ai_model_used = ai_model if message_type == 'ai_response' else ''
        response_time = round(processing_time / 1000, 2) if processing_time and message_type == 'ai_response' else None
        context = essential_context

        # Save to Central SQLite database
        db_path = 'db/laila_central.db'
        
        # Ensure database exists
        if not os.path.exists(db_path):
            from model.central_database_setup import create_central_database
            create_central_database()
        
        # Insert into central database
        conn = sqlite3.connect(db_path)
        conn.execute('''
            INSERT INTO chat_logs 
            (user_id, session_id, timestamp, module, sender, turn, message, ai_model, response_time_sec, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, chat_id, timestamp, module, sender, turn, message, ai_model_used, response_time, context))
        
        conn.commit()
        conn.close()
        

        
    except Exception as e:
        print(f"Error logging chat interaction to central database: {str(e)}")



# Initialize session ID for new users
def initialize_session():
    """Initialize session with unique IDs for tracking"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    if 'chat_id' not in session:
        session['chat_id'] = str(uuid.uuid4())

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key =  os.getenv('SECRET_KEY') or os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 604800  # 7 days (7 * 24 * 60 * 60)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['REMEMBER_COOKIE_DURATION'] = 2592000  # 30 days for remember me
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
CORS(app)  # Enable CORS for all routes

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

class User(UserMixin):
    def __init__(self, id, fullname, email, is_admin=False, is_confirmed = False):
        self.id = id
        self.fullname = fullname
        self.email = email
        self.is_admin = is_admin
        self.is_confirmed = is_confirmed
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(id):
    try:
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, fullname, email, is_admin, is_confirmed FROM users WHERE id = ?', (id,))
        user_data = cursor.fetchone()
        conn.close()
        print(user_data)
        if user_data:
            id, fullname, email, is_admin, is_confirmed = user_data
            return User(id, fullname, email, bool(is_admin), bool(is_confirmed))
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Import unified API settings with priority fallback

import google.generativeai as genai
from openai import OpenAI

# Configure Google AI with API key
genai.configure(api_key=get_api_key('google'))

# --- User Authentication ---



@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip().lower()  # Normalize email
        password = request.form.get('password', '')
        action = request.form.get('action', 'login')  # 'login' or 'register'
        remember_me = request.form.get('remember_me') == 'on'  # Checkbox value
        
        # Enhanced input validation
        if not email or not password:
            return render_template_string(LOGIN_TEMPLATE, 
                                        error="Both email and password are required.",
                                        email=email, show_register = action == 'register')
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[-1]:
            return render_template_string(LOGIN_TEMPLATE,
                                        error="Please enter a valid email address.",
                                        email=email, show_register = action == 'register')
        
        # Validate password length
        if len(password) < 6:
            return render_template_string(LOGIN_TEMPLATE,
                                        error="Password must be at least 6 characters long.",
                                        email=email)
        
        # Check if user exists in database
        try:
            conn = sqlite3.connect('db/laila_central.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, fullname, email, password_hash, is_confirmed FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if action == 'register':
                # Registration flow
                if not fullname or len(fullname.strip()) < 2:
                    conn.close()
                    return render_template_string(LOGIN_TEMPLATE, 
                                                error="Please enter your full name (at least 2 characters).",
                                                show_register=True, email=email)
                
                if user:
                    conn.close()
                    return render_template_string(LOGIN_TEMPLATE, 
                                                error="An account with this email already exists. Please use the login form instead.",
                                                email=email)
                
                # Create new user
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute('''
                    INSERT INTO users (fullname, email, password_hash, is_admin, created_at, is_confirmed, is_active)
                    VALUES (?, ?, ?, ?, datetime('now'),?, ?)
                ''', (fullname, email, hashed_password, False,  False, True))
                conn.commit()
                conn.close()
                return render_template_string(LOGIN_TEMPLATE, 
                                                info="Thank you for registering. An administrator will revise your account and grant you access.",
                                                email=email)
                # Log in the new user
                # user_obj = User(email, fullname, email)
                # # For registration, default to remember=True for better UX
                # login_user(user_obj, remember=True)
                # session.permanent = True
                
                # # Initialize session tracking
                # initialize_session()
                
                # print(f"✅ New user registered and logged in: {email}")
                # return redirect(url_for('main_menu'))
                
            else:
                # Login flow
                if not user:
                    conn.close()
                    return render_template_string(LOGIN_TEMPLATE, 
                                                error="No account found with this email address. Please check your email or register for a new account.",
                                                email=email)
                
                # Check password
                id, fullname, email_db, hashed_password, is_confirmed = user
                if is_confirmed == False:
                    return render_template_string(LOGIN_TEMPLATE, 
                                                error="Your account has not been confirmed yet.",
                                                email=email)
                # Handle both string and bytes password hashes
                if isinstance(hashed_password, str):
                    hash_to_check = hashed_password.encode('utf-8')
                else:
                    hash_to_check = hashed_password
                
                if bcrypt.checkpw(password.encode('utf-8'), hash_to_check):
                    # Update last login timestamp
                    try:
                        cursor.execute('''
                            UPDATE users SET last_login = datetime('now') WHERE email = ?
                        ''', (email,))
                        conn.commit()
                    except sqlite3.OperationalError as e:
                        print(f"⚠️  Warning: Could not update last_login: {e}")
                        # Continue with login even if last_login update fails
                    print(email)
                    user_obj = load_user(id)
                    login_user(user_obj, remember=remember_me)
                    session.permanent = True
                    
                    # Initialize session tracking
                    initialize_session()
                    
                    print(f"✅ Successful login: {email}")
                    print(f"   Remember me: {remember_me}")
                    print(f"   Session lifetime: {app.config['PERMANENT_SESSION_LIFETIME']/86400:.1f} days")
                    print(f"   Remember cookie lifetime: {app.config['REMEMBER_COOKIE_DURATION']/86400:.1f} days")
                    return redirect(url_for('main_menu'))
                else:
                    conn.close()
                    return render_template_string(LOGIN_TEMPLATE, 
                                                error="Incorrect password. Please try again or use 'Forgot your password?' to reset it.",
                                                email=email)
        
        except Exception as e:
            print(f"❌ Database error during login: {e}")
            import traceback
            traceback.print_exc()
            return render_template_string(LOGIN_TEMPLATE, 
                                        error="A system error occurred. Please try again in a moment.",
                                        email=email)

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    return render_template_string(LOGIN_TEMPLATE, show_register=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

# --- Missing Logging Functions ---
def log_user_interaction(user_id, interaction_type=None, page=None, action=None, element_id=None, element_type=None, element_value=None, additional_data=None):
    """Log user interactions to database"""

    try:
        timestamp = datetime.now().isoformat()
        
        # Use action as interaction_type if provided (for backwards compatibility)
        actual_interaction_type = action if action else interaction_type
        
        # Save to database
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        # Convert additional_data to string if it's a dict
        additional_data_str = str(additional_data) if additional_data else None
        
        cursor.execute('''
            INSERT INTO user_interactions 
            (user_id, interaction_type, page, action, element_id, element_type, element_value, timestamp, additional_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, actual_interaction_type, page, action, element_id, element_type, element_value, timestamp, additional_data_str))
        
        conn.commit()
        conn.close()
        
        # Also log to console for debugging
        print(f"✅ USER INTERACTION: {timestamp} | {user_id} | {actual_interaction_type} | {page}")
        if element_id:
            print(f"  Element: {element_type}#{element_id} = {element_value}")
            
    except Exception as e:
        print(f"❌ Error logging user interaction: {e}")

def log_data_analysis(user_id, analysis_type, input_data, generated_data, ai_model=None, processing_time=None, additional_context=None):
    """Log data analysis operations - simplified version"""
    try:
        timestamp = datetime.now().isoformat()
        print(f"DATA ANALYSIS: {timestamp} | {user_id} | {analysis_type} | Model: {ai_model} | Time: {processing_time}ms")
        print(f"  Input length: {len(input_data) if input_data else 0} chars")
        print(f"  Output length: {len(generated_data) if generated_data else 0} chars")
        if additional_context:
            print(f"  Context: {additional_context}")
    except Exception as e:
        print(f"Error logging data analysis: {e}")

# Unified AI function using API_Settings
def make_ai_call(prompt, system_prompt=None, service=None, model=None, user_api_key=None):
    """
    Make AI call using unified API system - Clean, Simple, Robust
    """
    try:
        # Use priority service if not specified (Google first, OpenAI fallback)
        if not service:
            config = get_ai_config()
            service = config['primary_service']
        
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
        if not api_key or api_key in ["your-google-api-key-here", "your-openai-api-key-here"]:
            config = get_ai_config()
            # Try fallback service if primary not available
            if config.get('fallback_service') and service != config['fallback_service']:
                print(f"🔄 Primary service {service} not available, switching to {config['fallback_service']}")
                return make_ai_call(prompt, system_prompt, config['fallback_service'], model, user_api_key)
            else:
                raise Exception(f"No valid API key available for {service}. Using test mode.")
        
        print(f"🎯 Using primary AI service: {service}, model: {model}")
        
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
            config = get_ai_config()
            if config.get('fallback_service') and service != config['fallback_service']:
                print(f"🔄 Trying fallback to {config['fallback_service']}...")
                try:
                    return make_ai_call(prompt, system_prompt, config['fallback_service'], None, None)
                except Exception as fallback_error:
                    print(f"Fallback also failed: {str(fallback_error)}")
        
        # Final fallback to test mode
        print("⚠️ All AI services failed, using test mode")
        return get_test_response(prompt, system_prompt), "test-mode"

def get_test_response(prompt, system_prompt=None):
    """Generate test response when no AI service is available"""
    if system_prompt and "bias" in system_prompt.lower():
        return """Thank you for sharing this content for bias analysis. In a real scenario, I would analyze this content for various forms of bias including:

1. **Gender bias** - Looking for stereotypical portrayals or assumptions
2. **Cultural bias** - Examining cultural assumptions or preferences  
3. **Socioeconomic bias** - Identifying class-based assumptions
4. **Confirmation bias** - Checking for one-sided perspectives
5. **Selection bias** - Looking at whose voices are included/excluded

*Note: This is a test response. Configure your API keys in API_Settings.py for full AI analysis.*

Would you like me to focus on any particular type of bias?"""
    
    elif system_prompt and "prompt" in system_prompt.lower():
        return """I'd be happy to help you create an effective AI prompt using the PCTFT framework! Let me start by understanding what you're trying to accomplish.

**PCTFT Framework:**
- **P**ersona: Who should the AI be?
- **C**ontext: What's the background?
- **T**ask: What specific action?
- **F**ormat: What output structure?
- **T**arget: Who's the audience?

*Note: This is a test response. Configure your API keys in API_Settings.py for full prompt engineering assistance.*

What kind of prompt are you looking to create?"""
    
    elif system_prompt and "data" in system_prompt.lower():
        return """I'd be happy to help you interpret your data! I can assist with:

- **Statistical Analysis**: Descriptive statistics, correlations, significance tests
- **Data Visualization**: Suggesting appropriate charts and graphs
- **Pattern Recognition**: Identifying trends and outliers
- **Academic Interpretation**: Relating findings to research questions

*Note: This is a test response. Configure your API keys in API_Settings.py for full data interpretation.*

Please share your data or describe what you'd like to analyze!"""
    
    else:
        return f"""Hello! I'm here to help with your questions. 

*Note: This is a test response. To enable full AI functionality, please configure your API keys in API_Settings.py*

Your message: "{prompt[:100]}{'...' if len(prompt) > 100 else ''}"

How can I assist you today?"""

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
def require_true_confirmed(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_confirmed', False):
            abort(403, description='Forbidden: Confirmed users only')
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@login_required
def admin():
    # Check if user is admin
    if not getattr(current_user, 'is_admin', False):
        return render_template_string(ADMIN_ACCESS_DENIED_TEMPLATE, 
                                    user_name=current_user.fullname or current_user.email)
    return send_file('views/admin.html')

@app.route('/test-connection')
@login_required
def test_connection():
    return send_file('views/test-connection.html')

@app.route('/story-form')
@login_required
def story_form():
    return send_file('views/story-form.html')

@app.route('/prompt-helper')
@login_required
def prompt_helper():
    return send_file('views/prompt-helper.html')

@app.route('/data-analyzer')
@login_required
def data_analyzer():
    return send_file('views/data-analyzer.html')

@app.route('/main-menu')
@login_required
def main_menu():
    return send_file('views/main-menu.html')

@app.route('/bias-research-platform')
@login_required
def bias_research_platform():
    return send_file('views/bias-research-platform.html')

@app.route('/chatbot-config')
@login_required
def chatbot_config():
    return send_file('views/chatbot-config.html')

@app.route('/chatbot-interface')
@login_required
def chatbot_interface():
    return send_file('views/chatbot-interface.html')

@app.route('/test-chatbots') # CHECK
@login_required
@require_true_admin
def test_chatbots():
    return send_file('views/test-chatbots.html')

@app.route('/user-settings')
@login_required
def user_settings():
    return send_file('views/user-settings.html')

@app.route('/analytics') # CHECK
@login_required
@require_true_admin
def analytics():
    return send_file('views/analytics.html')

@app.route('/logs')
@login_required
@require_true_admin
def logs():
    return send_file('views/logs.html')

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
            'user_id': current_user.id,
            'user_email': current_user.email,
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
        # log_interaction('settings_update', 'user_settings', 'save_settings', details=settings_data)
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        print(f"Error saving user settings: {str(e)}")
        return jsonify({'success': False, 'message': 'Error saving settings'}), 500

# --- Endpoint: Get User Information ---
@app.route('/api/user-info', methods=['GET'])
@login_required
def get_user_info():
    """Get current user information"""
    if current_user.is_authenticated:
        return jsonify({
            'user': {
                'id': current_user.id,
                'fullname': current_user.fullname,
                'email': current_user.email,
                'is_admin': getattr(current_user, 'is_admin', False)
            },
            'authenticated': True
        })
    else:
        return jsonify({'authenticated': False}), 401

# --- Endpoint: Session Status ---
@app.route('/api/session-status', methods=['GET'])
@login_required  
def session_status():
    """Get session status and expiration info"""
    from datetime import datetime, timedelta
    
    session_expires = None
    remember_expires = None
    
    if session.permanent:
        session_expires = datetime.now() + timedelta(seconds=app.config['PERMANENT_SESSION_LIFETIME'])
    
    # Check if remember cookie exists
    remember_token = request.cookies.get('remember_token')
    if remember_token:
        remember_expires = datetime.now() + timedelta(seconds=app.config['REMEMBER_COOKIE_DURATION'])
    
    return jsonify({
        'authenticated': True,
        'session_permanent': session.permanent,
        'session_expires': session_expires.isoformat() if session_expires else None,
        'remember_expires': remember_expires.isoformat() if remember_expires else None,
        'current_time': datetime.now().isoformat(),
        'session_lifetime_days': app.config['PERMANENT_SESSION_LIFETIME'] / 86400,
        'remember_lifetime_days': app.config['REMEMBER_COOKIE_DURATION'] / 86400
    })

# --- Endpoint: Get Field Explanations ---
@app.route('/api/field-help/<field_name>', methods=['GET'])
@login_required
def get_field_help(field_name):
    """Get explanation and example for a specific field"""
    # log_interaction('tool_usage', 'get_field_help', 'get_field_help', details={'field_name': field_name})
    explanation = get_field_explanation(field_name)
    return jsonify(explanation)

# --- Endpoint: Get Random Sample Data ---
@app.route('/api/sample-data/<field_name>', methods=['GET'])
@login_required
def get_sample_data(field_name):
    """Get random sample data for a specific field"""
    # log_interaction('tool_usage', 'get_sample_data', 'get_sample_data', details={'field_name': field_name})
    sample = get_random_example(field_name)
    return jsonify({'sample': sample})

# --- Endpoint: Get Configuration Info ---
@app.route('/api/config', methods=['GET'])
@login_required
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
@login_required
def get_ai_configuration():
    """Get comprehensive AI configuration for model selection"""
    from config import get_ai_configuration
    config = get_ai_configuration()
    return jsonify(config)

# --- Endpoint: Auto-fill Form with Sample Data ---
@app.route('/api/auto-fill', methods=['GET'])
@login_required
def auto_fill_form():
    """Generate a complete form filled with logically consistent sample data"""
    print("AUTO-FILL: Form auto-fill requested")
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
@login_required
@require_true_admin
def log_interaction_endpoint():
    """Log user interactions to CSV"""
    data = request.json
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    # Log detailed user interaction
    log_user_interaction(
        user_id=user_id,
        action=data.get('action', ''),
        page=data.get('page', ''),
        element_id=data.get('element_id'),
        element_type=data.get('element_type'),
        element_value=data.get('element_value'),
        additional_data={
            'interaction_type': data.get('interaction_type', ''),
            'details': data.get('details', ''),
            'ai_model': data.get('ai_model', ''),
            'ai_response': data.get('ai_response', ''),
            'session_data': data.get('session_data', '')
        }
    )
    
    return jsonify({'status': 'success', 'message': 'Interaction logged'})

# --- Endpoint: Log Chat Interaction ---
@app.route('/api/log-chat', methods=['POST'])
@login_required
@require_true_admin
def log_chat_endpoint():
    """Log chat interactions to CSV"""
    data = request.json
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    
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
@login_required
@require_true_admin
def get_user_interactions():
    """Get user interaction logs from database"""
    print(f"🔍 User interactions API called by user: {getattr(current_user, 'email', 'anonymous') if current_user.is_authenticated else 'not authenticated'}")
    try:
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ui.timestamp,
                u.email as user_email,
                u.fullname as user_name,
                ui.interaction_type,
                ui.page,
                ui.action,
                ui.element_id,
                ui.element_type,
                ui.element_value,
                ui.additional_data
            FROM user_interactions ui
            LEFT JOIN users u ON ui.user_id = u.id
            ORDER BY ui.timestamp DESC
            LIMIT 1000
        """)
        
        columns = ['timestamp', 'user_email', 'user_name', 'interaction_type', 'page', 'action', 'element_id', 'element_type', 'element_value', 'additional_data']
        interactions = []
        for row in cursor.fetchall():
            interaction_dict = {}
            for i, column in enumerate(columns):
                value = row[i]
                # Fix additional_data JSON formatting
                if column == 'additional_data':
                    if value:
                        try:
                            # Convert Python dict string to proper JSON
                            import json
                            if isinstance(value, str) and value.startswith('{'):
                                # Replace single quotes with double quotes for JSON
                                json_str = value.replace("'", '"')
                                # Validate it's proper JSON
                                parsed = json.loads(json_str)
                                value = json_str
                            else:
                                value = json.dumps(str(value))
                        except:
                            # If parsing fails, set to null to avoid JSON issues
                            value = None
                    else:
                        # Set empty values to null for JSON safety
                        value = None
                interaction_dict[column] = value
            # Add aliases for compatibility
            interaction_dict['user_id'] = interaction_dict['user_email']
            interactions.append(interaction_dict)
        
        conn.close()
        print(f"✅ User interactions API returning {len(interactions)} records")
        return jsonify({'success': True, 'interactions': interactions})
        
    except Exception as e:
        print(f"❌ Error loading user interactions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error loading user interactions'}), 500

# --- Endpoint: Get Chat Logs ---
@app.route('/api/chat-logs', methods=['GET'])
@login_required
@require_true_admin
def get_chat_logs():
    """Get chat logs from database"""
    print(f"🔍 Chat logs API called by user: {getattr(current_user, 'email', 'anonymous') if current_user.is_authenticated else 'not authenticated'}")
    try:
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cl.timestamp,
                u.email as user_email,
                u.fullname as user_name,
                cl.module,
                cl.sender,
                cl.turn,
                cl.message,
                cl.ai_model,
                cl.response_time_sec,
                cl.context
            FROM chat_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            ORDER BY cl.timestamp DESC
            LIMIT 1000
        """)
        
        columns = ['timestamp', 'user_email', 'user_name', 'module', 'sender', 'turn', 'message', 'ai_model', 'response_time_sec', 'context']
        chats = []
        for row in cursor.fetchall():
            chat_dict = {}
            for i, column in enumerate(columns):
                chat_dict[column] = row[i]
            # Add aliases for compatibility
            chat_dict['chat_type'] = chat_dict['module']
            chat_dict['message_type'] = chat_dict['sender'].lower() + '_message'
            chat_dict['user_id'] = chat_dict['user_email']
            chats.append(chat_dict)
        
        conn.close()
        print(f"✅ Chat logs API returning {len(chats)} records")
        return jsonify({'success': True, 'chats': chats})
        
    except Exception as e:
        print(f"❌ Error loading chat logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error loading chat logs'}), 500

# --- Endpoint: Get Data Analysis Logs ---
@app.route('/api/data-analysis-logs', methods=['GET'])
@login_required
@require_true_admin
def get_data_analysis_logs():
    """Get data analysis logs from database"""
    try:
        # For now, return data analysis entries from chat logs where module is 'Data Interpreter'
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cl.timestamp,
                u.email as user_email,
                u.fullname as user_name,
                cl.message,
                cl.ai_model,
                cl.response_time_sec,
                cl.context
            FROM chat_logs cl
            LEFT JOIN users u ON cl.user_id = u.id
            WHERE cl.module = 'Data Interpreter'
            ORDER BY cl.timestamp DESC
            LIMIT 500
        """)
        
        analyses = []
        for row in cursor.fetchall():
            analyses.append({
                'timestamp': row[0],
                'user_id': row[1],
                'user_name': row[2],
                'analysis_type': 'Data Interpretation',
                'input_data_sample': row[3][:200] + '...' if len(str(row[3])) > 200 else row[3],
                'generated_data_sample': 'See chat logs for full analysis',
                'ai_model': row[4],
                'processing_time_ms': int(row[5] * 1000) if row[5] else None,
                'context': row[6]
            })
        
        conn.close()
        return jsonify({'success': True, 'analyses': analyses})
        
    except Exception as e:
        print(f"Error loading data analysis logs: {str(e)}")
        return jsonify({'success': False, 'message': 'Error loading data analysis logs'}), 500

# --- Endpoint: Get Logs Statistics ---
@app.route('/api/logs-statistics', methods=['GET'])
@login_required
@require_true_admin
def get_logs_statistics():
    """Get statistics from database"""
    try:
        stats = {}
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM chat_logs WHERE user_id IS NOT NULL")
        stats['total_users'] = cursor.fetchone()[0] or 0
        
        # Total chat messages
        cursor.execute("SELECT COUNT(*) FROM chat_logs")
        stats['total_chats'] = cursor.fetchone()[0] or 0
        
        # Total interactions (same as total chats for now)
        stats['total_interactions'] = stats['total_chats']
        
        # Data analysis count
        cursor.execute("SELECT COUNT(*) FROM chat_logs WHERE module = 'Data Interpreter'")
        stats['total_analyses'] = cursor.fetchone()[0] or 0
        
        # Average processing time (in milliseconds)
        cursor.execute("SELECT AVG(response_time_sec) FROM chat_logs WHERE response_time_sec IS NOT NULL AND sender = 'AI'")
        avg_time_sec = cursor.fetchone()[0]
        stats['avg_processing_time'] = int(avg_time_sec * 1000) if avg_time_sec else 0
        
        # Most active user
        cursor.execute("""
            SELECT u.email, COUNT(*) as message_count 
            FROM chat_logs cl 
            LEFT JOIN users u ON cl.user_id = u.id 
            WHERE u.email IS NOT NULL 
            GROUP BY u.email 
            ORDER BY message_count DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        stats['most_active_user'] = result[0] if result else 'N/A'
        
        conn.close()
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
    
    print(f"FORM SUBMIT: Story form submitted with {len(data)} fields")
    # Add timestamp and user_id if not present
    if 'ID' not in data:
        from datetime import datetime
        data['ID'] = int(datetime.now().timestamp())
    
    # Save form data to CSV (simple approach without pandas)
    import csv
    import os
    
    # Define data file
    DATA_FILE = 'submissions.csv'
    
    # Write to CSV file
    file_exists = os.path.exists(DATA_FILE)
    
    with open(DATA_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = list(data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        
        # Write header only if file doesn't exist
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(data)
    
    return jsonify({'status': 'success', 'message': 'Data saved successfully'})

# --- Endpoint: Admin CSV Export ---
@app.route('/api/export', methods=['GET'])
@login_required
@require_true_admin
def export_csv():
    if not os.path.exists(DATA_FILE):
        return jsonify({'error': 'No data available'}), 404
    return send_file(DATA_FILE, mimetype='text/csv', as_attachment=True, download_name='submissions.csv')

# --- Endpoint: AI Chat about Vignette ---
@app.route('/api/chat', methods=['POST'])
@login_required
def vignette_chat():
    data = request.json
    vignette = data.get('vignette')
    user_message = data.get('message')
    
    if not vignette or not user_message:
        return jsonify({'error': 'Both vignette and message are required'}), 400
    
    # Log user input for vignette chat
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.id,
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
            user_id=current_user.id,
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
@login_required
def student_bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    
    if not vignette:
        return jsonify({'error': 'Vignette required'}), 400
    
    # Log user input for student bias analysis
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.id,
        chat_type='student_bias_analysis',
        message_type='user_input',
        content=vignette,
        context_data={
            'vignette_length': len(vignette),
            'analysis_type': 'bias_analysis'
        }
    )
    
    try:
        # Load system prompt from text file
        system_prompt = load_system_prompt('bias_analyst')
        
        # Use default AI service configuration
        ai_service = 'google'
        ai_model = 'gemini-1.5-pro'
        
        # Use bias analyst chatbot for analysis
        prompt = f"""Vignette to analyze:\n{vignette}\n\nPlease provide your bias analysis following the guidelines above. This analysis is for educational purposes to help the student understand potential biases in academic scenarios."""
        
        result, model = make_ai_call(prompt, system_prompt, service=ai_service, model=ai_model)
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=current_user.id,
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
@login_required
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
        user_id=current_user.id,
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
        
        # Load system prompt from text file
        system_prompt = load_system_prompt('prompt_helper')
        
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
            user_id=current_user.id,
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
@login_required
def prompt_discussion():
    data = request.json
    user_message = data.get('message')
    current_prompt = data.get('current_prompt')
    
    if not user_message or not current_prompt:
        return jsonify({'error': 'Message and current prompt required'}), 400
    
    # Log user input for prompt discussion
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.id,
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
            user_id=current_user.id,
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
@login_required
def analyze_data():
    data = request.json
    data_content = data.get('data')
    data_type = data.get('data_type', 'text')
    
    if not data_content:
        return jsonify({'error': 'Data content required'}), 400
    
    # Log user input for data analysis
    start_time = time.time()
    log_chat_interaction(
        user_id=current_user.id,
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
            user_id=current_user.id,
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
            fallback_analysis = f"""I apologize, but I'm having trouble analyzing your data right now. Here's some general guidance for data interpretation in educational research:\n\n**General Interpretation Framework:**\n- **Descriptive Summary**: What does the data show at face value?\n- **Patterns and Trends**: What patterns emerge from the analysis?\n- **Educational Significance**: How do these findings relate to learning and teaching?\n- **Practical Implications**: What actions might educators take based on these results?\n- **Limitations**: What are the constraints and caveats of this analysis?\n\nPlease try again with a smaller data sample or check the format."""
        
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
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    log_user_interaction(user_id, 'data_interpretation_request', 'data_analyzer', additional_data={
        'data_type': data_type,
        'analysis_type': analysis_type,
        'audience_level': audience_level,
        'data_length': len(data_content),
        'research_context': research_context,
        'target_insights': target_insights
    })
    
    try:
        # Load system prompt from text file
        system_prompt = load_system_prompt('data_interpreter')
        
        # Create comprehensive interpretation prompt
        interpretation_prompt = f"""INTERPRETATION REQUEST:\n\nResearch Context: {research_context if research_context else 'General educational research context'}\n\nAnalysis Type: {analysis_type if analysis_type else 'General statistical analysis'}\n\nTarget Insights: {target_insights if target_insights else 'General interpretation and educational implications'}\n\nAudience Level: {audience_level}\n\nData Type: {data_type}\n\nData to Interpret:\n{data_content}\n\nPlease provide a comprehensive interpretation following the framework outlined in the system prompt. Focus on the educational research perspective and tailor the complexity to the specified audience level."""
        
        # Use the specified AI service and model
        result, model = make_ai_call(
            interpretation_prompt, 
            system_prompt, 
            service=ai_service, 
            model=ai_model, 
            user_api_key=user_api_key
        )
        
        processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Log AI response
        log_chat_interaction(
            user_id=user_id,
            chat_type='data_interpreter',
            message_type='ai_response',
            content=result,
            context_data={
                'data_type': data_type,
                'analysis_type': analysis_type,
                'audience_level': audience_level,
                'research_context': research_context,
                'target_insights': target_insights,
                'input_data_sample': data_content[:500]
            },
            ai_model=model,
            ai_response=result,
            processing_time=processing_time
        )
        
        # Log data analysis operation
        log_data_analysis(
            user_id=user_id,
            analysis_type=f'data_interpretation_{data_type}',
            input_data=data_content,
            generated_data=result,
            ai_model=model,
            processing_time=processing_time,
            additional_context={
                'research_context': research_context,
                'target_insights': target_insights,
                'audience_level': audience_level
            }
        )
        
        return jsonify({'analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Data Interpretation Error: {str(e)}")
        
        # Provide fallback interpretation based on analysis type
        if analysis_type == 'statistical_test':
            fallback_analysis = f"""I apologize, but I'm having trouble interpreting your statistical test results right now. Here's some general guidance for interpreting statistical tests in educational research:\n\n**Key Elements to Consider:**\n- **Statistical Significance**: Look at p-values (typically p < 0.05 indicates significance)\n- **Effect Size**: Consider practical significance, not just statistical significance\n- **Confidence Intervals**: These provide a range of plausible values\n- **Educational Implications**: What do these results mean for teaching and learning?\n\nFor a more detailed interpretation, please try again or consult with a statistician."""
        
        elif analysis_type == 'network_analysis':
            fallback_analysis = f"""I apologize, but I'm having trouble interpreting your network analysis right now. Here's some general guidance for network analysis in educational research:\n\n**Key Network Metrics:**\n- **Centrality Measures**: Who are the key players in the network?\n- **Clustering**: Are there distinct groups or communities?\n- **Density**: How connected is the network overall?\n- **Educational Applications**: How do these patterns relate to learning, collaboration, or communication?\n\nFor a more detailed interpretation, please try again with a smaller dataset."""
        
        else:
            fallback_analysis = f"""I apologize, but I'm having trouble interpreting your data right now. Here's some general guidance for data interpretation in educational research:\n\n**General Interpretation Framework:**\n- **Descriptive Summary**: What does the data show at face value?\n- **Patterns and Trends**: What patterns emerge from the analysis?\n- **Educational Significance**: How do these findings relate to learning and teaching?\n- **Practical Implications**: What actions might educators take based on these results?\n- **Limitations**: What are the constraints and caveats of this analysis?\n\nPlease try again with a smaller data sample or check the format."""
        
        return jsonify({'analysis': fallback_analysis, 'status': 'success'})

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
    user_email = current_user.id if current_user.is_authenticated else 'anonymous'
    log_chat_interaction(
        user_id=user_id,
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
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    log_chat_interaction(
        user_id=user_id,
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
            user_id=user_id,
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
@login_required
def bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    api_key = data.get('api_key')
    service = data.get('service', AI_SERVICE)
    
    # log_interaction('user_input', 'bias_analysis', 'request_bias_analysis', details={'vignette': vignette})
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
            prompt = f"""{load_bias_analysis_prompt()}\n            \nVignette to analyze:\n{vignette}\n            \nPlease provide your bias analysis following the guidelines above."""
            
            response = model.generate_content(prompt)
            result = response.text
            # log_interaction('ai_response', 'bias_analysis', 'bias_analysis_response', details={'vignette': vignette}, ai_model=model_name, ai_response=result)
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
            # log_interaction('ai_response', 'bias_analysis', 'bias_analysis_response', details={'vignette': vignette}, ai_model='gpt-3.5-turbo', ai_response=result)
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
@require_true_admin
def database_stats():
    """Get database statistics for admin interface"""
    try:
        from model.central_database_admin import CentralDatabase
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
@require_true_admin
def export_chat_logs():
    """Export chat logs to CSV with filtering options"""
    try:
        from model.central_database_admin import CentralDatabase
        
        data = request.json or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        module = data.get('module')
        user_filter = data.get('user')
        
        # If no dates provided, default to full range (earliest to latest)
        if not date_from and not date_to:
            # Get earliest and latest timestamps from database
            db_temp = CentralDatabase()
            conn = sqlite3.connect('db/laila_central.db')
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM chat_logs')
                min_date, max_date = cursor.fetchone()
                if min_date and max_date:
                    date_from = min_date.split('T')[0]  # Extract date part
                    date_to = max_date.split('T')[0]    # Extract date part
                    print(f"📅 Default export range: {date_from} to {date_to}")
            except:
                pass  # If table doesn't exist or is empty, leave dates as None
            finally:
                conn.close()
        
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
@require_true_admin
def export_users():
    """Export users data to CSV"""
    try:
        from model.central_database_admin import CentralDatabase
        
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
@require_true_admin
def export_interactions():
    """Export user interactions to CSV"""
    try:
        from model.central_database_admin import CentralDatabase
        
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
@require_true_admin
def export_submissions():
    """Export user submissions to CSV"""
    try:
        from model.central_database_admin import CentralDatabase
        
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
@require_true_admin
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
        conn = sqlite3.connect('db/laila_central.db')
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
        conn = sqlite3.connect('db/laila_central.db')
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
        from model.central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Generate internal name from display name
        import re
        internal_name = re.sub(r'[^a-zA-Z0-9_]', '_', data['display_name'].lower())
        
        conn = sqlite3.connect('db/laila_central.db')
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
        
        conn = sqlite3.connect('db/laila_central.db')
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
        
        conn = sqlite3.connect('db/laila_central.db')
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
        
        conn = sqlite3.connect('db/laila_central.db')
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

# --- Admin User Management Functions ---
@app.route('/api/admin/users')
@login_required
@require_true_admin
def admin_get_users():
    """Get all users for admin management"""
    try:
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT email, fullname, is_admin, created_at, is_active, is_confirmed 
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            email, fullname, is_admin, created_at, is_active, is_confirmed = row
            users.append({
                'email': email,
                'fullname': fullname,
                'is_admin': bool(is_admin),
                'is_confirmed': bool(is_confirmed),
                'created_at': created_at,
                'is_active': bool(is_active)
            })
        
        conn.close()
        return jsonify(users)
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500
    
# --- Endpoint: Confirm user ---
@app.route('/api/admin/users/confirm', methods=['POST'])
@login_required
@require_true_admin
def confirm_user():
    """Confirm a user's email address (admin only)"""
    try:
        data = request.json
        print(data)
        email = data.get('email', '')
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        email = email.strip().lower()
        # Check if user exists
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT email, fullname FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Hash new password
        
        # Update password
        cursor.execute('UPDATE users SET is_confirmed = ? WHERE email = ?', (True, email))
        conn.commit()
        conn.close()
        
        print(f"✅ Admin {current_user.email} confirmed user {email}")
        
        return jsonify({
            'message': f'Confirmed account successfully for {email}',
            'email': email
        })
    except Exception as e:
        print(f"❌ Error in user confirmation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to reset user'}), 500

@app.route('/api/admin/reset-password', methods=['POST'])
@login_required
@require_true_admin
def admin_reset_password():
    """Reset a user's password (admin only)"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        new_password = data.get('new_password', '')
        
        if not email or not new_password:
            return jsonify({'error': 'Email and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Check if user exists
        conn = sqlite3.connect('db/laila_central.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT email, fullname FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Hash new password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update password
        cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', 
                      (password_hash, email))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Admin {current_user.email} reset password for user {email}")
        
        return jsonify({
            'message': f'Password reset successfully for {email}',
            'user': email
        })
        
    except Exception as e:
        print(f"❌ Error in admin password reset: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to reset password'}), 500

# --- Endpoints: Custom Chatbot User Interface ---
@app.route('/api/chatbots/available')
@login_required
def get_available_chatbots():
    """Get all active chatbots for users"""
    try:
        conn = sqlite3.connect('db/laila_central.db')
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
        from model.central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create conversation record
        conn = sqlite3.connect('db/laila_central.db')
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
        from model.central_database_admin import CentralDatabase
        db = CentralDatabase()
        user_info = db.get_user_by_email(current_user.email)
        user_id = user_info['id'] if user_info else None
        
        # Get chatbot configuration
        conn = sqlite3.connect('db/laila_central.db')
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
        conn = sqlite3.connect('db/laila_central.db')
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
        
        conn = sqlite3.connect('db/laila_central.db')
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
@app.route('/chatbot-admin')
@login_required
@require_true_admin
def chatbot_admin():
    return send_file('views/chatbot-admin.html')

@app.route('/custom-chatbots')
@login_required
@require_true_admin
def custom_chatbots():
    return send_file('views/custom-chatbots.html')

# --- Endpoints: System Chatbots ---
@app.route('/api/system-chatbots/available')
@login_required
def get_system_chatbots():
    """Get all active system chatbots"""
    try:
        # Define available system chatbots with their metadata
        available_prompts = list_available_prompts()
        
        system_chatbots = [
            {
                'id': 1,
                'name': 'research_helper',
                'display_name': 'Research Methods Helper',
                'description': available_prompts['research_helper'],
                'greeting_message': 'Hello! I\'m here to help you with research methodology, statistical analysis, and study design. What would you like to explore?'
            },
            {
                'id': 2, 
                'name': 'welcome_assistant',
                'display_name': 'LAILA Welcome Assistant',
                'description': available_prompts['welcome_assistant'],
                'greeting_message': 'Welcome to LAILA! I\'m here to help you navigate the platform and get started with our research tools. How can I assist you today?'
            },
            {
                'id': 3,
                'name': 'bias_analyst', 
                'display_name': 'Bias Analysis Expert',
                'description': available_prompts['bias_analyst'],
                'greeting_message': 'Hi there! I specialize in identifying and analyzing bias in educational content. Share something you\'d like me to examine for potential bias.'
            },
            {
                'id': 4,
                'name': 'prompt_helper',
                'display_name': 'Prompt Engineering Assistant', 
                'description': available_prompts['prompt_helper'],
                'greeting_message': 'Hello! I\'ll help you create better AI prompts using the PCTFT framework. Share your initial prompt idea and I\'ll guide you through improving it.'
            }
        ]
        
        return jsonify({
            'success': True,
            'chatbots': system_chatbots
        })
        
    except Exception as e:
        print(f"ERROR in get_system_chatbots: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system-chatbots/chat', methods=['POST'])
@login_required
def system_chatbot_chat():
    """Chat with system chatbots"""
    try:
        data = request.json
        chatbot_name = data.get('chatbot_name')
        user_message = data.get('message')
        
        if not chatbot_name or not user_message:
            return jsonify({'success': False, 'error': 'Chatbot name and message required'}), 400
        
        # Load system prompt from text file
        system_prompt = load_system_prompt(chatbot_name)
        
        # Check if prompt was loaded successfully
        if system_prompt.startswith("Unknown prompt name") or system_prompt.startswith("Prompt file not found") or system_prompt.startswith("Error loading"):
            return jsonify({'success': False, 'error': f'Chatbot not found: {chatbot_name}'}), 404
        
        # Use default AI service configuration
        ai_service = 'google'
        ai_model = 'gemini-1.5-flash'
        
        # Get AI response using the make_ai_call function
        start_time = time.time()
        try:
            ai_response, model_used = make_ai_call(
                prompt=user_message,
                system_prompt=system_prompt,
                service=ai_service,
                model=ai_model
            )
        except Exception as ai_error:
            print(f"AI call error: {ai_error}")
            ai_response = f"I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
            model_used = ai_model
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log the chat interaction
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        
        # Store to user database chat logs
        try:
            user_conn = sqlite3.connect('db/laila_central.db')
            user_cursor = user_conn.cursor()
            
            session_id = f"system_chat_{chatbot_name}_{int(time.time())}"
            
            # Log user message
            user_cursor.execute('''
                INSERT INTO chat_logs 
                (user_id, session_id, timestamp, module, sender, turn, message, ai_model, response_time_sec, context)
                VALUES ((SELECT id FROM users WHERE email = ?), ?, datetime('now'), ?, 'User', 1, ?, ?, ?, ?)
            ''', (user_id, session_id, f'system_chatbot_{chatbot_name}', user_message, model_used, response_time/1000, chatbot_name))
            
            # Log AI response
            user_cursor.execute('''
                INSERT INTO chat_logs 
                (user_id, session_id, timestamp, module, sender, turn, message, ai_model, response_time_sec, context)
                VALUES ((SELECT id FROM users WHERE email = ?), ?, datetime('now'), ?, 'AI', 2, ?, ?, ?, ?)
            ''', (user_id, session_id, f'system_chatbot_{chatbot_name}', ai_response, model_used, response_time/1000, chatbot_name))
            
            user_conn.commit()
            user_conn.close()
        except Exception as log_error:
            print(f"Logging error: {log_error}")
            # Continue even if logging fails
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'model_used': model_used,
            'response_time': response_time,
            'chatbot_name': chatbot_name
        })
        
    except Exception as e:
        print(f"ERROR in system_chatbot_chat: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("==================================================")
    print("LAILA API Configuration Status")
    print("==================================================")
    print(f"Default Service: {DEFAULT_AI_SERVICE}")
    print(f"Google AI Available: {is_service_available('google')}")
    print(f"OpenAI Available: {is_service_available('openai')}")
    print("✅ Configuration is valid!")
    print("==================================================")
    print()
    print("Starting Flask server...")
    print("Backend will be available at: http://localhost:5001")
    print("Test page: http://localhost:5001/test-connection")
    print("Admin panel: http://localhost:5001/admin")
    print("Chatbot admin: http://localhost:5001/chatbot-admin")
    app.run(debug=True, host='0.0.0.0', port=5001)