from API_Settings import get_ai_config, log_api_status

print("Testing get_ai_config:")
config = get_ai_config()
print(f"Primary service: {config.get('primary_service', 'NOT FOUND')}")
print(f"Fallback service: {config.get('fallback_service', 'NOT FOUND')}")

print("\nTesting log_api_status:")
log_api_status()
