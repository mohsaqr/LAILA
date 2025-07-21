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
    <link rel="stylesheet" href="styles.css">
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
            max-width: 400px;
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
        }
        
        .toggle-form {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
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
            <p class="subtitle">Learn AI and LA Platform</p>
            
            {% if error %}
            <div class="error-message">
                {{ error }}
            </div>
            {% endif %}
            
            <div class="login-form" id="loginForm">
                <form action="/login" method="post">
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <input type="hidden" name="action" value="login">
                    <button type="submit" class="button">Login</button>
                </form>
                <p>Don't have an account? <a href="#" class="toggle-form" onclick="toggleForm()">Register here</a></p>
            </div>
            
            <div class="register-form hidden" id="registerForm">
                <form action="/login" method="post">
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
                        <input type="password" id="reg-password" name="password" required>
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
        
        {% if show_register %}
        // Show register form by default if show_register is True
        document.addEventListener('DOMContentLoaded', function() {
            toggleForm();
        });
        {% endif %}
    </script>
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
        with open('bias-analysis-system-prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Bias analysis prompt file not found. Please ensure 'bias-analysis-system-prompt.txt' exists."
    except Exception as e:
        return f"Error loading bias analysis prompt: {str(e)}"

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
