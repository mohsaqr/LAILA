#!/bin/bash

# LAAI Installation Script
# This script sets up the LAAI platform for immediate use

echo "🚀 LAILA - Learn AI and LA Platform Installation"
echo "==============================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "🎯 Next Steps:"
echo "1. Configure your API keys in config.py (optional)"
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo "3. Open http://localhost:5001 in your browser"
echo ""
echo "📚 For detailed instructions, see README.md"
echo ""
echo "🎉 Happy researching with LAILA!"
