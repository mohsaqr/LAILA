#!/usr/bin/env python3
"""
System Prompts Manager for LAILA Platform
Lists all available system prompts stored as text files
"""
import os
from config import list_available_prompts, load_system_prompt

def list_all_prompts():
    """List all available system prompts with details"""
    print("=" * 60)
    print("📝 LAILA SYSTEM PROMPTS - TEXT FILE BASED")
    print("=" * 60)
    
    prompts = list_available_prompts()
    
    print(f"Found {len(prompts)} system prompts:\n")
    
    for prompt_name, description in prompts.items():
        # Try to load the prompt to get file info
        content = load_system_prompt(prompt_name)
        
        if not content.startswith("Error") and not content.startswith("Unknown"):
            # Find corresponding text file
            filename = None
            if prompt_name == 'bias_analyst':
                filename = 'prompts/bias-analysis-system-prompt.txt'
            elif prompt_name == 'prompt_helper':
                filename = 'prompts/prompt-helper-system-prompt.txt'
            elif prompt_name == 'data_interpreter':
                filename = 'prompts/interpret-data-system-prompt.txt'
            elif prompt_name == 'research_helper':
                filename = 'prompts/research-helper-system-prompt.txt'
            elif prompt_name == 'welcome_assistant':
                filename = 'prompts/welcome-assistant-system-prompt.txt'
            
            if filename and os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"✅ {prompt_name}")
                print(f"   📄 File: {filename}")
                print(f"   📊 Size: {file_size} bytes ({len(content)} chars)")
                print(f"   📝 Description: {description}")
                print()
            else:
                print(f"❌ {prompt_name}")
                print(f"   📄 File: {filename} (NOT FOUND)")
                print(f"   📝 Description: {description}")
                print()
        else:
            print(f"❌ {prompt_name}")
            print(f"   ⚠️  Error: {content}")
            print(f"   📝 Description: {description}")
            print()
    
    print("=" * 60)
    print("💡 BENEFITS OF TEXT FILE PROMPTS:")
    print("   • Easy to edit with any text editor")
    print("   • Version control friendly (git)")
    print("   • No database dependencies")
    print("   • Direct file access for debugging")
    print("   • Simple backup and sharing")
    print("=" * 60)

def show_prompt_content(prompt_name):
    """Show the content of a specific prompt"""
    content = load_system_prompt(prompt_name)
    
    print(f"\n📝 PROMPT CONTENT: {prompt_name}")
    print("=" * 60)
    print(content)
    print("=" * 60)
    print(f"Character count: {len(content)}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        prompt_name = sys.argv[1]
        show_prompt_content(prompt_name)
    else:
        list_all_prompts()
        print("\n💡 To view a specific prompt:")
        print("   python3 list_prompts.py <prompt_name>")
        print("   Example: python3 list_prompts.py bias_analyst") 