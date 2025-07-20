# 🚀 LAILA Quick Start Guide

Get up and running with LAILA in under 5 minutes!

## 📋 Prerequisites

- Python 3.8+ installed on your system
- Internet connection (for AI services)

## ⚡ Installation (Choose One)

### Option 1: Automatic Installation

**Linux/Mac:**
```bash
./install.sh
```

**Windows:**
```cmd
install.bat
```

### Option 2: Manual Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
```

## 🎯 Running LAILA

1. **Activate virtual environment** (if not already active):
   ```bash
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate.bat  # Windows
   ```

2. **Start the server**:
   ```bash
   python app.py
   ```

3. **Open your browser** and go to:
   ```
   http://localhost:5001
   ```

## 🎮 First Steps

1. **Try Quick Story Generator**:
   - Click "Quick Story Generator"
   - Select options from dropdowns
   - Click "Generate Story"
   - Click "Continue to Chat" for AI analysis

2. **Explore Comparison Stories**:
   - Click "Generate Comparison Stories"
   - Choose Gender or Geographic comparison
   - Generate contrasting vignettes
   - Analyze differences with AI

3. **Use Interactive Story Builder**:
   - Click "Interactive Story Builder"
   - Fill detailed form
   - Generate comprehensive vignettes

## 🔧 Optional: Configure AI Services

Edit `config.py` to add your API keys:

```python
# For OpenAI GPT models
OPENAI_API_KEY = "your-openai-key-here"

# For Google Gemini models  
GOOGLE_API_KEY = "your-google-key-here"
```

**Note**: The platform works without API keys using test mode!

## 🆘 Need Help?

- **Port already in use?** Change `PORT = 5001` in `config.py`
- **Dependencies not installing?** Make sure virtual environment is activated
- **AI not responding?** Check API keys or use test mode

## 📚 Learn More

See `README.md` for complete documentation and advanced features.

---

**You're ready to start researching with LAILA! 🎉**
