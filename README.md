# LAILA - Learn AI and LA Platform

A comprehensive academic AI assistant platform for research, education, and learning analytics.

## 🎯 Overview

LAILA (Learn AI and LA) is a comprehensive web application designed for academic researchers, educators, and students. The platform provides an intuitive interface for AI-powered research tools, educational assistance, and learning analytics with a focus on bias detection and academic support.

## ✨ Features

### 🖊️ Interactive Story Builder
- Guided storytelling interface for detailed vignette creation
- Step-by-step form with validation
- Academic context-aware prompts

### ⚡ Quick Story Generator
- Rapid vignette creation with dropdown selections
- Minimal input required
- Instant story generation

### ⚖️ Comparison Story Generator
- **Gender Comparison**: Generate contrasting male/female scenarios
- **Geographic Comparison**: Global South vs Global North perspectives
- Side-by-side analysis with discussion prompts

### 🤖 AI-Powered Chat Analysis
- Seamless integration with AI models (OpenAI GPT & Google Gemini)
- Bias detection and analysis
- Interactive discussions about generated vignettes
- Educational conversation flow

### 📊 Data Collection & Analytics
- User interaction tracking
- Session management
- CSV data export capabilities
- Research-focused data structure

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Extract the LAILA package** to your desired directory
2. **Navigate to the LAILA folder**:
   ```bash
   cd LAILA
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure API keys** (see Configuration section below)

6. **Run the application**:
   ```bash
   python app.py
   ```

7. **Access the platform**:
   - Open your browser and go to: `http://localhost:5001`
   - The bias research platform will be available immediately

## ⚙️ Configuration

### API Keys Setup

Edit the `config.py` file to configure your AI services:

```python
# OpenAI Configuration (Optional - for GPT models)
OPENAI_API_KEY = "your-openai-api-key-here"

# Google AI Configuration (Optional - for Gemini models)
GOOGLE_API_KEY = "your-google-api-key-here"

# Server Configuration
PORT = 5001
DEBUG = True
```

### AI Service Options

The platform supports multiple AI services:

1. **OpenAI GPT Models** (requires OpenAI API key)
   - GPT-4, GPT-3.5-turbo
   - High-quality bias analysis
   - Requires paid API access

2. **Google Gemini** (requires Google AI API key)
   - Gemini Pro models
   - Free tier available
   - Good performance for bias detection

3. **Test Mode** (no API key required)
   - Mock responses for development
   - Perfect for testing the interface

### Getting API Keys

#### OpenAI API Key:
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Go to API Keys section
4. Create a new API key
5. Add it to `config.py` in the `OPENAI_API_KEY` field

#### Google AI API Key:
1. Visit [Google AI Studio](https://makersuite.google.com/)
2. Create a new project or select existing
3. Generate an API key
4. Add it to `config.py` in the `GOOGLE_API_KEY` field

### Admin Panel Access

The platform includes an admin panel for data management:

1. **Access**: Navigate to `http://localhost:5001/admin.html`
2. **Authentication**: Use the admin token (default: `supersecret`)
3. **Features**:
   - Download all submissions as CSV
   - Perform bias analysis on vignettes
   - View system statistics
4. **Configuration**: Change the admin token in `config.py` (`ADMIN_TOKEN`)

## 📁 File Structure

```
LAILA/
├── app.py                              # Flask backend server
├── config.py                          # Configuration and API keys
├── requirements.txt                    # Python dependencies
├── styles.css                         # CSS styling
├── index.html                         # Main menu (entry point)
├── bias-research-platform.html        # Bias research toolkit
├── story-form.html                    # Interactive story builder
├── chat.html                          # AI chat interface
├── prompt-helper.html                 # Prompt engineering tool
├── data-analyzer.html                 # Data interpretation tool
├── chatbot-config.html                # Educational chatbot configurator
├── admin.html                         # Admin panel
├── bias-analysis-system-prompt.txt    # AI system prompt for bias analysis
├── prompt-helper-system-prompt.txt    # Prompt engineering AI prompt
├── interpret-data-system-prompt.txt   # Data interpretation AI prompt
└── README.md                          # This documentation
```

## 🎮 Usage Guide

### 1. Creating Vignettes

#### Interactive Story Builder
- Click "Interactive Story Builder" for detailed vignette creation
- Fill out the comprehensive form with academic details
- Generate contextual stories based on your inputs

#### Quick Story Generator
- Click "Quick Story Generator" for rapid creation
- Select from dropdown options (country, pronouns, field, progress)
- Generate instant academic scenarios

#### Comparison Stories
- Click "Generate Comparison Stories"
- Choose between Gender or Geographic comparisons
- Generate side-by-side contrasting vignettes

### 2. AI Analysis

After generating any vignette:
1. Click "Continue to Chat" button
2. The vignette is automatically sent to the AI chat
3. Engage in bias analysis discussions
4. Ask follow-up questions about potential biases

### 3. Research Applications

- **Bias Detection Training**: Use for educational purposes
- **Research Data Collection**: Generate diverse academic scenarios
- **Comparative Analysis**: Study differences in vignette presentation
- **AI Ethics Education**: Explore bias in AI-generated content

## 🔧 Customization

### Adding New Vignette Templates

Edit the JavaScript in `index.html` to add new scenario templates:

```javascript
const newScenarios = [
    {
        title: "Your Scenario Title",
        content: "Your scenario description..."
    }
];
```

### Modifying AI Prompts

Edit `bias-analysis-system-prompt.txt` to customize the AI's analysis approach:

```
You are an expert in educational bias detection...
[Customize the prompt for your specific needs]
```

### Styling Changes

Modify `styles.css` to change the visual appearance:

```css
.option-button {
    /* Customize button appearance */
}
```

## 🛠️ Technical Details

### Backend (Flask)
- RESTful API endpoints
- Session management
- Data persistence
- AI service integration

### Frontend (HTML/CSS/JavaScript)
- Responsive design
- Interactive forms
- Real-time updates
- Modern UI components

### AI Integration
- Multiple AI service support
- Configurable models
- Error handling
- Fallback options

## 📊 Data Collection

The platform automatically tracks:
- User interactions
- Vignette generations
- Chat sessions
- Bias analysis requests
- Session timestamps

Data is stored in CSV format for research analysis.

## 🔒 Security & Privacy

- No personal data collection beyond session tracking
- API keys stored locally in config file
- No data transmission to external services (except AI APIs)
- Local data storage only

## 🚨 Troubleshooting

### Common Issues

1. **Port 5001 already in use**:
   ```bash
   # Change port in config.py or kill existing process
   lsof -ti:5001 | xargs kill -9
   ```

2. **Module not found errors**:
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **AI not responding**:
   - Check API keys in `config.py`
   - Verify internet connection
   - Try test mode first

4. **CSS/JS not loading**:
   - Clear browser cache
   - Check file paths
   - Restart the server

### Support

For technical issues:
1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure API keys are correctly configured
4. Test with different browsers

## 📈 Deployment

### Local Development
- Use the built-in Flask development server
- Perfect for research and testing

### Production Deployment
For production use, consider:
- Using a production WSGI server (Gunicorn, uWSGI)
- Setting up reverse proxy (Nginx)
- Configuring proper security headers
- Using environment variables for API keys

Example production setup:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## 📝 License

This project is designed for academic and research use. Please ensure compliance with your institution's policies and AI service terms of use.

## 🤝 Contributing

To extend the platform:
1. Add new vignette templates
2. Implement additional AI services
3. Enhance the user interface
4. Add new analysis features

## 📞 Contact

For questions about implementation or research applications, refer to your local technical support or the original development team.

---

**LAILA - Empowering academic research through AI-assisted learning analytics**
