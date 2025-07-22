# Enhanced Configuration file for Academic Research Data Collection Platform
import os
import random
import csv

# =============================================================================
# IMPORT UNIFIED API SETTINGS
# =============================================================================
# All AI/API configuration is now handled in API_Settings.py
from API_Settings import (
    get_ai_config, get_api_key, get_default_model, get_model_info,
    is_service_available, validate_configuration, log_api_status,
    DEFAULT_AI_SERVICE, AI_MODELS
)

# =============================================================================
# AUTHENTICATION TEMPLATES
# =============================================================================

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAILA - Login</title>
    <link rel="stylesheet" href="static/css/unified-styles.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Arial', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            max-width: 450px;
            width: 100%;
            padding: 20px;
        }
        
        .main-content {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        
        .main-title {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        .subtitle {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s ease;
            margin-bottom: 15px;
        }
        
        .button:hover {
            transform: translateY(-2px);
        }
        
        .button.secondary {
            background: #6c757d;
        }
        

        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
            text-align: left;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #c3e6cb;
            text-align: left;
        }
        
        .info-message {
            background: #cce7ff;
            color: #004085;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #99d3ff;
            text-align: left;
        }
        
        .toggle-form {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
            cursor: pointer;
        }
        
        .toggle-form:hover {
            text-decoration: underline;
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-content">
            <h1 class="main-title">LAILA</h1>
            <p class="subtitle"><b>L</b>earn with <b>AI LA</b>boratory</p>
            
            {% if error %}
            <div class="error-message">
                <strong>Error:</strong> {{ error }}
            </div>
            {% endif %}
            
            {% if success %}
            <div class="success-message">
                <strong>Success:</strong> {{ success }}
            </div>
            {% endif %}
            
            {% if info %}
            <div class="info-message">
                <strong>Info:</strong> {{ info }}
            </div>
            {% endif %}
            
            <div class="login-form" id="loginForm">
                <form action="/" method="post">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required value="{{ email or '' }}">
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <div class="form-group" style="display: flex; align-items: center; text-align: left;">
                        <input type="checkbox" id="remember_me" name="remember_me" checked style="margin-right: 8px; width: auto;">
                        <label for="remember_me" style="margin-bottom: 0; font-weight: normal; color: #666;">Keep me logged in for 30 days</label>
                    </div>
                    <input type="hidden" name="action" value="login">
                    <button type="submit" class="button">Login</button>
                </form>
                <p>
                    Don't have an account? <a href="#" class="toggle-form" onclick="toggleForm()">Register here</a><br>
                    <small style="color: #666;">Need password reset? Contact an administrator.</small>
                </p>
            </div>
            
            <div class="register-form hidden" id="registerForm" {% if show_register %}style="display: block;"{% endif %}>
                <form action="/" method="post">
                    <div class="form-group">
                        <label for="reg-fullname">Full Name</label>
                        <input type="text" id="reg-fullname" name="fullname" required>
                    </div>
                    <div class="form-group">
                        <label for="reg-email">Email</label>
                        <input type="email" id="reg-email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="reg-password">Password</label>
                        <input type="password" id="reg-password" name="password" required minlength="6">
                        <small style="color: #666;">Password must be at least 6 characters long</small>
                    </div>
                    <input type="hidden" name="action" value="register">
                    <button type="submit" class="button">Register</button>
                </form>
                <p>Already have an account? <a href="#" class="toggle-form" onclick="toggleForm()">Login here</a></p>
            </div>
            

        </div>
    </div>
    
    <script>
        function toggleForm() {
            const loginForm = document.getElementById('loginForm');
            const registerForm = document.getElementById('registerForm');
            
            if (loginForm.classList.contains('hidden')) {
                loginForm.classList.remove('hidden');
                registerForm.classList.add('hidden');
            } else {
                loginForm.classList.add('hidden');
                registerForm.classList.remove('hidden');
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            {% if show_register %}
            toggleForm();
            {% endif %}
        });
    </script>
</body>
</html>
"""

# Admin Access Denied Template
ADMIN_ACCESS_DENIED_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Access Required - LAILA</title>
    <link rel="stylesheet" href="static/css/unified-styles.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Arial', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            max-width: 500px;
            width: 100%;
            padding: 20px;
        }
        
        .main-content {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        
        .crown-icon {
            font-size: 4em;
            color: #e74c3c;
            margin-bottom: 20px;
        }
        
        .main-title {
            color: #2c3e50;
            font-size: 2.2em;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        .subtitle {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 25px;
            line-height: 1.5;
        }
        
        .user-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }
        
        .button {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s ease;
            margin: 10px;
        }
        
        .button:hover {
            transform: translateY(-2px);
        }
        
        .contact-info {
            margin-top: 30px;
            padding: 20px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            color: #856404;
        }
        
        .contact-info h4 {
            margin-top: 0;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-content">
            <div class="crown-icon">
                <i class="fas fa-crown"></i>
            </div>
            
            <h1 class="main-title">Admin Access Required</h1>
            
            <p class="subtitle">
                Sorry {{ user_name }}, you need administrator privileges to access the admin panel.
            </p>
            
            <div class="user-info">
                <strong>Your Account:</strong> {{ user_name }}<br>
                <strong>Account Type:</strong> Standard User
            </div>
            
            <div class="contact-info">
                <h4><i class="fas fa-info-circle"></i> Need Admin Access?</h4>
                <p>If you believe you should have administrator access, please contact the system administrator to have your account upgraded.</p>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/main-menu" class="button">
                    <i class="fas fa-home"></i> Return to Main Menu
                </a>
                
                <a href="/logout" class="button" style="background: #6c757d;">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/js/all.min.js"></script>
</body>
</html>
"""

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

# System prompt for AI chat with students about vignettes
CHAT_SYSTEM_PROMPT = """You are an educational AI assistant helping students discuss and analyze academic vignettes for research purposes. Your role is to:

1. **Encourage Critical Thinking**: Ask probing questions that help students analyze different aspects of the vignette
2. **Provide Multiple Perspectives**: Help students see the scenario from various viewpoints (student, instructor, institution)
3. **Educational Guidance**: Offer insights about learning theories, educational psychology, and support strategies
4. **Supportive Tone**: Maintain an encouraging, non-judgmental approach that promotes learning
5. **Research Context**: Remember these vignettes are for academic research on education and support systems
6. **Give your opinon**: Remember to answer questions and give your perspectives too if asked, don't ask too much. 
6. ** You give some persepective if asked, students want to learn and get how you think about it.

Guidelines:
- Ask follow-up questions to deepen analysis
- Encourage students to consider factors like cultural background, learning approach, and support effectiveness
- Help identify potential biases or assumptions in the scenarios
- Connect discussions to broader educational concepts
- Keep responses conversational, short and engaging (2-4 sentences typically)

Remember: You're facilitating learning and critical thinking, not providing definitive answers."""

# Bias analysis prompt is now loaded from external file
def load_bias_analysis_prompt():
    """Load bias analysis prompt from external file"""
    try:
        with open('prompts/bias-analysis-system-prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Bias analysis prompt file not found. Please ensure 'bias-analysis-system-prompt.txt' exists in the 'prompts' folder."
    except Exception as e:
        return f"Error loading bias analysis prompt: {str(e)}"

def load_system_prompt(prompt_name):
    """Load any system prompt from text files
    
    Args:
        prompt_name: Name of the prompt (e.g., 'bias_analyst', 'prompt_helper', etc.)
    
    Returns:
        str: The prompt content, or error message if not found
    """
    # Map prompt names to file names
    prompt_files = {
        'bias_analyst': 'bias-analysis-system-prompt.txt',
        'bias_analysis': 'bias-analysis-system-prompt.txt',
        'prompt_helper': 'prompt-helper-system-prompt.txt',
        'data_interpreter': 'interpret-data-system-prompt.txt',
        'research_helper': 'research-helper-system-prompt.txt',
        'welcome_assistant': 'welcome-assistant-system-prompt.txt'
    }
    
    filename = prompt_files.get("prompts/" + prompt_name)
    if not filename:
        return f"Unknown prompt name: {prompt_name}. Available prompts: {list(prompt_files.keys())}"
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            print(f"✅ Loaded prompt '{prompt_name}' from {filename} ({len(content)} chars)")
            return content
    except FileNotFoundError:
        return f"Prompt file not found: {filename}. Please ensure the file exists."
    except Exception as e:
        return f"Error loading prompt from {filename}: {str(e)}"

def list_available_prompts():
    """List all available system prompts"""
    return {
        'bias_analyst': 'Bias analysis expert for educational content',
        'prompt_helper': 'Prompt engineering assistant using PCTFT framework',  
        'data_interpreter': 'Data analysis and interpretation expert',
        'research_helper': 'Educational research methods assistant',
        'welcome_assistant': 'Platform welcome and navigation helper'
    }

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Admin Configuration
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'supersecret')

# File Configuration
DATA_FILE = 'submissions.csv'
DEBUG_MODE = True
SHOW_AI_MODEL_DEBUG = True  # Set to False to hide AI model info

# Server Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5001

# =============================================================================
# HELPER FUNCTIONS (Updated to use API_Settings)
# =============================================================================

def get_ai_configuration():
    """Get the current AI configuration (updated to use unified system)"""
    config = get_ai_config()
    
    # Format for backward compatibility
    return {
        'default_service': config['default_service'],
        'available_models': {
            'openai': [{'id': k, **v} for k, v in config['openai']['models'].items()],
            'google': [{'id': k, **v} for k, v in config['google']['models'].items()]
        },
        'default_openai_model': config['openai']['default_model'],
        'default_google_model': config['google']['default_model'],
        'system_google_key_available': config['google']['available'],
        'system_openai_key_available': config['openai']['available'],
        'chat_prompt': CHAT_SYSTEM_PROMPT,
        'bias_prompt': load_bias_analysis_prompt()
    }

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_config():
    """Validate the configuration settings"""
    issues = []
    
    if not ADMIN_TOKEN:
        issues.append("ADMIN_TOKEN is required")
    
    # Validate API configuration
    api_issues = validate_configuration()
    issues.extend(api_issues)
    
    return issues

# Run validation on import
_validation_issues = validate_config()
if _validation_issues:
    print("Configuration Issues Found:")
    for issue in _validation_issues:
        print(f"  - {issue}")
    print("\nPlease fix these issues before running the application.")
else:
    # Log API status on successful validation
    log_api_status()
