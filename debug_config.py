from API_Settings import get_ai_config, is_service_available

print("Testing is_service_available:")
print(f"Google available: {is_service_available('google')}")
print(f"OpenAI available: {is_service_available('openai')}")

print("\nTesting get_ai_config (step by step):")
try:
    config = get_ai_config()
    print(f"Config type: {type(config)}")
    print(f"Config keys: {list(config.keys())}")
    print(f"Config: {config}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
