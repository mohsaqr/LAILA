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
