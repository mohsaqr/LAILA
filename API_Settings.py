# =============================================================================
# UNIFIED API SETTINGS - LAILA Platform
# =============================================================================
# This file contains all AI service configurations in one place
# Clean, Simple, Robust, and Reliable API management

import os
import logging
from dotenv import load_dotenv

load_dotenv()
# =============================================================================
# PRIMARY API KEYS (Main Configuration)
# =============================================================================
# Add your API keys here - these are the primary keys used by the system


# =============================================================================
# AI SERVICE CONFIGURATION
# =============================================================================

# Default AI service to use ('google' or 'openai')
DEFAULT_AI_SERVICE = "google"

# Export these for backward compatibility
DEFAULT_GOOGLE_MODEL = "gemini-1.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

# Available models for each service
AI_MODELS = {
    'google': {
        'default': 'gemini-1.5-flash',
        'models': {
            'gemini-1.5-flash': {
                'name': 'Gemini 1.5 Flash (Fast)',
                'description': 'Quick responses with good quality',
                'max_tokens': 8192
            },
            'gemini-1.5-pro': {
                'name': 'Gemini 1.5 Pro (Advanced)', 
                'description': 'Most capable Gemini model for complex tasks',
                'max_tokens': 32768
            },
            'gemini-pro': {
                'name': 'Gemini Pro (Standard)',
                'description': 'Reliable performance for most tasks',
                'max_tokens': 4096
            }
        }
    },
    'openai': {
        'default': 'gpt-4o-mini',
        'models': {
            'gpt-4o-mini': {
                'name': 'GPT-4o Mini (Fast & Efficient)',
                'description': 'Best for quick analysis and cost-effective processing',
                'max_tokens': 16384
            },
            'gpt-4o': {
                'name': 'GPT-4o (Advanced)',
                'description': 'Most capable model for complex analysis', 
                'max_tokens': 4096
            },
            'gpt-4-turbo': {
                'name': 'GPT-4 Turbo (Balanced)',
                'description': 'Good balance of capability and speed',
                'max_tokens': 4096
            },
            'gpt-3.5-turbo': {
                'name': 'GPT-3.5 Turbo (Basic)',
                'description': 'Basic analysis capabilities, fastest response',
                'max_tokens': 4096
            }
        }
    }
}

# =============================================================================
# API CONFIGURATION FUNCTIONS
# =============================================================================

def get_api_key(service, user_key=None):
    """
    Get API key for specified service with proper fallback logic
    Priority: user_key > environment variable > configured key
    """
    if user_key and user_key.strip():
        return user_key.strip()
    
    # Check environment variables
    if service == 'google':
        env_key = os.getenv('GOOGLE_API_KEY')
        print(env_key)
        if env_key:
            return env_key
        return GOOGLE_API_KEY if GOOGLE_API_KEY.strip() else None
    
    elif service == 'openai':
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            return env_key
        return OPENAI_API_KEY if OPENAI_API_KEY.strip() else None
    
    return None

def get_default_model(service):
    """Get the default model for a service"""
    if service in AI_MODELS:
        return AI_MODELS[service]['default']
    return None

def get_model_info(service, model_id):
    """Get detailed information about a specific model"""
    if service in AI_MODELS and model_id in AI_MODELS[service]['models']:
        return AI_MODELS[service]['models'][model_id]
    return None

def get_available_models(service):
    """Get list of available models for a service"""
    if service in AI_MODELS:
        return AI_MODELS[service]['models']
    return {}

def is_service_available(service):
    """Check if a service has a valid API key configured"""
    api_key = get_api_key(service)
    return api_key is not None and len(api_key.strip()) > 10

def get_ai_config():
    """Get complete AI configuration with Google priority fallback system"""
    google_available = is_service_available('google')
    openai_available = is_service_available('openai')
    
    # Priority logic: Google first, OpenAI as fallback
    if google_available:
        primary_service = 'google'
        fallback_service = 'openai' if openai_available else None
    elif openai_available:
        primary_service = 'openai'
        fallback_service = None
    else:
        primary_service = 'google'  # Default, will use test mode
        fallback_service = None
    
    return {
        'default_service': primary_service,
        'primary_service': primary_service,
        'fallback_service': fallback_service,
        'available_services': [primary_service] + ([fallback_service] if fallback_service else []),
        'google': {
            'available': google_available,
            'default_model': get_default_model('google'),
            'models': get_available_models('google')
        },
        'openai': {
            'available': openai_available,
            'default_model': get_default_model('openai'),
            'models': get_available_models('openai')
        }
    }
    return issues

def get_fallback_service():
    """Get a fallback service if the default one is not available"""
    if is_service_available(DEFAULT_AI_SERVICE):
        return DEFAULT_AI_SERVICE
    
    # Try other services
    for service in AI_MODELS.keys():
        if service != DEFAULT_AI_SERVICE and is_service_available(service):
            return service
    
    return None

# =============================================================================
# LOGGING AND DEBUGGING
# =============================================================================

def log_api_status():
    """Log the current API configuration status"""
    config = get_ai_config()
    issues = validate_configuration()
    
    print("\n" + "="*50)
    print("LAILA API Configuration Status")
    print("="*50)
    print(f"Default Service: {DEFAULT_AI_SERVICE}")
    print(f"Google AI Available: {config['google']['available']}")
    print(f"OpenAI Available: {config['openai']['available']}")
    
    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("\n✅ Configuration is valid!")
    
    fallback = get_fallback_service()
    if fallback and fallback != DEFAULT_AI_SERVICE:
        print(f"🔄 Fallback service available: {fallback}")
    
    print("="*50 + "\n")

# =============================================================================
# ENVIRONMENT VARIABLE SUPPORT
# =============================================================================
# You can also set API keys via environment variables:
# export GOOGLE_API_KEY="your_key_here"
# export OPENAI_API_KEY="your_key_here"

# Run validation on import
def validate_configuration():
    """Validate the current API configuration and return any issues"""
    issues = []
    
    # Check if at least one service is available
    google_available = is_service_available('google')
    openai_available = is_service_available('openai')
    
    if not google_available and not openai_available:
        issues.append("No valid API keys found. Please configure at least one service.")
    
    # Check default service
    if DEFAULT_AI_SERVICE not in AI_MODELS:
        issues.append(f"Invalid default service: {DEFAULT_AI_SERVICE}")
    elif not is_service_available(DEFAULT_AI_SERVICE):
        issues.append(f"Default service '{DEFAULT_AI_SERVICE}' has no valid API key")
    
    return issues

if __name__ == "__main__":
    log_api_status()
