# Enhanced Configuration file for Academic Research Data Collection Platform
import os
import random

# =============================================================================
# AI SERVICE CONFIGURATION
# =============================================================================

# Default AI service: 'google' or 'openai'
DEFAULT_AI_SERVICE = 'openai'  # Default service when no user preference is set

# System API Keys (fallback when user doesn't provide their own)
GOOGLE_API_KEY = ""  # Add your Google AI API key here
OPENAI_API_KEY = ""  # Add your OpenAI API key here

# Available AI Models for User Selection
AVAILABLE_MODELS = {
    'openai': [
        {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini (Fast & Efficient)', 'description': 'Best for quick analysis and cost-effective processing'},
        {'id': 'gpt-4o', 'name': 'GPT-4o (Advanced)', 'description': 'Most capable model for complex analysis'},
        {'id': 'gpt-4-turbo', 'name': 'GPT-4 Turbo (Balanced)', 'description': 'Good balance of capability and speed'},
        {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo (Basic)', 'description': 'Basic analysis capabilities, fastest response'}
    ],
    'google': [
        {'id': 'gemini-1.5-flash', 'name': 'Gemini 1.5 Flash (Fast)', 'description': 'Quick responses with good quality'},
        {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro (Advanced)', 'description': 'Most capable Gemini model for complex tasks'},
        {'id': 'gemini-pro', 'name': 'Gemini Pro (Standard)', 'description': 'Reliable performance for most tasks'}
    ]
}

# Default models
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GOOGLE_MODEL = "gemini-1.5-flash"

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
# HELPER FUNCTIONS
# =============================================================================


def get_ai_config():
    """Get the current AI configuration"""
    return {
        'default_service': DEFAULT_AI_SERVICE,
        'available_models': AVAILABLE_MODELS,
        'default_openai_model': DEFAULT_OPENAI_MODEL,
        'default_google_model': DEFAULT_GOOGLE_MODEL,
        'system_google_key_available': bool(GOOGLE_API_KEY),
        'system_openai_key_available': bool(OPENAI_API_KEY),
        'chat_prompt': CHAT_SYSTEM_PROMPT,
        'bias_prompt': load_bias_analysis_prompt()
    }

def get_model_info(service, model_id):
    """Get information about a specific model"""
    if service in AVAILABLE_MODELS:
        for model in AVAILABLE_MODELS[service]:
            if model['id'] == model_id:
                return model
    return None

def get_api_key(service, user_key=None):
    """Get API key for a service, preferring user key over system key"""
    if user_key:
        return user_key
    
    if service == 'openai':
        return OPENAI_API_KEY
    elif service == 'google':
        return GOOGLE_API_KEY
    
    return None

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_config():
    """Validate the configuration settings"""
    issues = []
    
    if DEFAULT_AI_SERVICE not in ['google', 'openai']:
        issues.append("DEFAULT_AI_SERVICE must be either 'google' or 'openai'")
    
    if not ADMIN_TOKEN:
        issues.append("ADMIN_TOKEN is required")
    
    # Check if at least one system API key is available
    if not GOOGLE_API_KEY and not OPENAI_API_KEY:
        issues.append("At least one system API key (Google or OpenAI) should be configured")
    
    return issues

# Run validation on import
_validation_issues = validate_config()
if _validation_issues:
    print("Configuration Issues Found:")
    for issue in _validation_issues:
        print(f"  - {issue}")
    print("\nPlease fix these issues before running the application.")
