import os
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import pandas as pd
import openai
import google.generativeai as genai
from io import StringIO
from functools import wraps
from enhanced_config import *

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

# Configure default AI services
genai.configure(api_key=GOOGLE_API_KEY)
from openai import OpenAI

# Helper function to make AI calls with flexible service/model selection
def make_ai_call(prompt, system_prompt=None, service=None, model=None, user_api_key=None):
    """Make AI call using specified service and model"""
    try:
        # Use defaults if not specified
        if not service:
            service = DEFAULT_AI_SERVICE
        if not model:
            model = DEFAULT_OPENAI_MODEL if service == 'openai' else DEFAULT_GOOGLE_MODEL
        
        # Get API key (user key takes priority)
        api_key = get_api_key(service, user_api_key)
        if not api_key:
            raise Exception(f"No API key available for {service}")
        
        if service == 'google':
            # Configure Google AI with the appropriate key
            if user_api_key:
                genai.configure(api_key=user_api_key)
            else:
                genai.configure(api_key=GOOGLE_API_KEY)
            
            model_instance = genai.GenerativeModel(model)
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt
            response = model_instance.generate_content(full_prompt)
            return response.text
            
        elif service == 'openai':
            # Create OpenAI client with the appropriate key
            client = OpenAI(api_key=api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        else:
            raise Exception(f"Unsupported AI service: {service}")
    except Exception as e:
        print(f"AI Call Error ({service}/{model}): {str(e)}")
        raise e

# --- Helper: Admin Auth Decorator ---
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Admin-Token')
        if token != ADMIN_TOKEN:
            abort(403, description='Forbidden: Invalid admin token')
        return f(*args, **kwargs)
    return decorated

# --- Test Endpoint ---
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend is running!'})

# --- Serve HTML files ---
@app.route('/')
def index():
    return send_file('main-menu.html')

@app.route('/index.html')
def traditional_form():
    return send_file('index.html')

@app.route('/admin.html')
def admin():
    return send_file('admin.html')

@app.route('/test-connection.html')
def test_connection():
    return send_file('test-connection.html')

@app.route('/chat.html')
def chat():
    return send_file('chat.html')

@app.route('/story-form.html')
def story_form():
    return send_file('story-form.html')

@app.route('/prompt-helper.html')
def prompt_helper():
    return send_file('prompt-helper.html')

@app.route('/data-analyzer.html')
def data_analyzer():
    return send_file('data-analyzer.html')

@app.route('/main-menu.html')
def main_menu():
    return send_file('main-menu.html')

@app.route('/bias-research-platform.html')
def bias_research_platform():
    return send_file('bias-research-platform.html')

@app.route('/chatbot-config.html')
def chatbot_config():
    return send_file('chatbot-config.html')

@app.route('/chatbot-interface.html')
def chatbot_interface():
    return send_file('chatbot-interface.html')

# --- Endpoint: Get Field Explanations ---
@app.route('/api/field-help/<field_name>', methods=['GET'])
def get_field_help(field_name):
    """Get explanation and example for a specific field"""
    explanation = get_field_explanation(field_name)
    return jsonify(explanation)

# --- Endpoint: Get Random Sample Data ---
@app.route('/api/sample-data/<field_name>', methods=['GET'])
def get_sample_data(field_name):
    """Get random sample data for a specific field"""
    sample = get_random_example(field_name)
    return jsonify({'sample': sample})

# --- Endpoint: Get Configuration Info ---
@app.route('/api/config', methods=['GET'])
def get_config_info():
    """Get current configuration information (legacy endpoint)"""
    config = get_ai_config()
    # Legacy format for backward compatibility
    legacy_config = {
        'service': config['default_service'],
        'google_key_available': config['system_google_key_available'],
        'openai_key_available': config['system_openai_key_available']
    }
    return jsonify(legacy_config)

# --- Endpoint: Get AI Configuration ---
@app.route('/api/ai-config', methods=['GET'])
def get_ai_configuration():
    """Get comprehensive AI configuration for model selection"""
    config = get_ai_config()
    return jsonify(config)

# --- Endpoint: Auto-fill Form with Sample Data ---
@app.route('/api/auto-fill', methods=['GET'])
def auto_fill_form():
    """Generate a complete form filled with logically consistent sample data"""
    import random
    
    # Define positive and negative behaviors for logical consistency
    positive_behaviors = [
        'is highly conscientious consistently demonstrating organization and self-discipline in their studies',
        'shows a high need for cognition actively engaging in complex problem-solving and effortful thinking',
        'has strong performance self-efficacy believing in their ability to succeed in specific academic tasks',
        'is intrinsically motivated learning for the inherent satisfaction and interest in the subject matter',
        'exhibits excellent effort regulation persisting with difficult or uninteresting academic tasks',
        'effectively uses time and study management strategies to plan and allocate their learning activities',
        'demonstrates strong metacognitive skills by planning monitoring and evaluating their own learning processes',
        'proactively seeks help from instructors and peers when encountering difficulties',
        'employs a deep approach to learning focusing on understanding the meaning and connections between concepts',
        'feels a strong sense of academic and social integration within the university community'
    ]
    
    negative_behaviors = [
        'consistently procrastinates delaying the start and completion of academic tasks',
        'is motivated by an avoidance goal orientation focusing more on not failing than on achieving success',
        'experiences high levels of test anxiety which negatively impacts their exam performance',
        'utilizes a surface approach to learning memorizing information just enough to pass without deeper understanding',
        'is under a high degree of academic stress due to coursework and deadlines',
        'has a high level of extraversion that appears to negatively correlate with performance possibly due to prioritizing social activities',
        'exhibits symptoms of depression which is impacting their academic outcomes',
        'struggles with general life stress which spills over and affects their academic work',
        'lacks effective self-regulatory strategies leading to disorganized study habits',
        'avoids challenging tasks and gives up easily when faced with academic difficulty'
    ]
    
    positive_analytics = [
        'a consistent pattern of submitting assignments well before the deadline which is often coupled with early and regular access to the associated learning resources',
        'a pattern of watching instructional videos to completion and contributing insightful well-structured posts in discussion forums that build upon and extend course concepts',
        'consistently high scores on exams and quizzes often achieved with minimal attempts which signals a strong and confident grasp of the course material',
        'frequent logins throughout the week at regular times resulting in a high overall time-on-site and a sustained active presence in the course environment',
        'data showing significant time spent on challenging tasks and a high course completion rate indicating the student is on track and applying themselves diligently',
        'a logical sequence of activity within the learning management system such as reviewing lecture notes and optional readings before attempting related assessments',
        'active central participation in group projects supported by positive peer assessment ratings from teammates'
    ]
    
    negative_analytics = [
        'a recurring pattern of submitting assignments at the last minute which is directly preceded by intense short bursts of platform activity after long periods of inactivity',
        'consistently low or failing scores on exams and quizzes often coupled with multiple failed attempts signaling a poor understanding of core concepts',
        'a pattern of skipping through instructional videos or watching less than a quarter of them combined with discussion posts that are short off-topic or add no value',
        'infrequent logins a very low overall time-on-site and a general lack of digital presence in the learning environment',
        'minimal time spent on tasks avoidance of challenging modules and a stalled course completion rate with many overdue items'
    ]
    
    positive_decisions = [
        'advanced enrichment opportunities', 'research collaboration opportunities', 'independent study options',
        'maintain current support level', 'peer mentorship opportunities', 'advanced project opportunities',
        'independent research track', 'collaborative learning enhancement', 'thesis research support',
        'peer mentorship program', 'accelerated coursework', 'honors program admission',
        'research assistant position', 'dissertation fellowship', 'lab research opportunity',
        'teaching assistant role', 'coding bootcamp advancement', 'clinical placement priority',
        'conference presentation opportunity', 'student leadership role', 'MBA honors track',
        'engineering competition team', 'medical residency preparation', 'creative writing workshop',
        'undergraduate research grant'
    ]
    
    negative_decisions = [
        'intensive academic support', 'remedial coursework', 'anxiety management support',
        'study skills training', 'stress management program', 'time management counseling',
        'mental health support services', 'holistic wellness program', 'study skills workshop',
        'academic resilience training', 'procrastination intervention', 'confidence building program',
        'test preparation support', 'deep learning strategies', 'stress reduction techniques',
        'academic focus training', 'counseling and academic support'
    ]
    
    # Decide if this will be a positive or negative scenario
    is_positive_scenario = random.choice([True, False])
    
    if is_positive_scenario:
        # Positive scenario: good behavior → good analytics → good outcomes
        behavior = random.choice(positive_behaviors)
        analytics = random.choice(positive_analytics)
        progress = 'well'
        support_hours = random.randint(1, 3)  # Less support needed
        support_decision = random.choice(positive_decisions)
        support_result = random.randint(85, 100)  # High scores
        completion_status = 'completed'
    else:
        # Negative scenario: poor behavior → poor analytics → poor outcomes
        behavior = random.choice(negative_behaviors)
        analytics = random.choice(negative_analytics)
        progress = 'poorly'
        support_hours = random.randint(4, 8)  # More support needed
        support_decision = random.choice(negative_decisions)
        support_result = random.randint(45, 75)  # Lower scores
        completion_status = random.choice(['dropped out of', 'continued with'])
    
    # Generate consistent form data
    form_data = {
        'Nationality': random.choice(SAMPLE_DATA['nationalities']),
        'Pronoun': random.choice(['his', 'her', 'their']),
        'Student_State_Trait_Behaviour': behavior,
        'Degree_Level': random.choice(['K12 School', 'Bachelor\'s Degree', 'Master\'s Degree', 'Doctoral Degree']),
        'Field_of_Study': random.choice(['Computer Science', 'Psychology', 'Mathematics', 'Nursing', 'Business Administration', 'Engineering', 'Chemistry', 'Medicine', 'Physics', 'Sociology', 'Literature', 'Philosophy', 'Environmental Science', 'History', 'Biology']),
        'Progress_Descriptor': progress,
        'Learning_Analytics': analytics,
        'Support_Hours': support_hours,
        'Support_Period': random.choice(['Per Week', 'Per Month']),
        'Support_Delivery_Method': random.choice(['By the teacher', 'At home (self-directed)', 'By a senior peer']),
        'Support_Decision': support_decision,
        'Support_Duration': random.choice(['One semester', 'Six weeks', 'Two months', 'One month', 'Other']),
        'Support_Result': support_result,
        'Completion_Status': completion_status
    }
    
    return jsonify(form_data)

# --- Endpoint: Log User Interaction ---
@app.route('/api/log-interaction', methods=['POST'])
def log_interaction():
    """Log user interactions to CSV"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Add timestamp and ensure user_id is present
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': data.get('user_id', 'anonymous'),
        'interaction_type': data.get('interaction_type', 'unknown'),
        'page': data.get('page', 'unknown'),
        'action': data.get('action', 'unknown'),
        'details': data.get('details', ''),
        'session_data': str(data.get('session_data', ''))
    }
    
    df = pd.DataFrame([interaction_data])
    
    # Save to interactions CSV file
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df.to_csv(interactions_file, index=False, sep=';')
    else:
        df.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    return jsonify({'status': 'success', 'message': 'Interaction logged'})

# --- Endpoint: Submit Form Data ---
@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Add timestamp and user_id if not present
    if 'ID' not in data:
        data['ID'] = int(pd.Timestamp.now().timestamp())
    
    user_id = data.get('user_id', 'anonymous')
    
    # Log the form submission
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'form_submission',
        'page': 'main_form',
        'action': 'submit_form',
        'details': f'Form submitted with ID: {data["ID"]}',
        'session_data': f'nationality: {data.get("Nationality", "")}, field: {data.get("Field_of_Study", "")}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    # Save form data
    df = pd.DataFrame([data])
    
    # Use semicolon separator to match existing format
    if not os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE, index=False, sep=';')
    else:
        df.to_csv(DATA_FILE, mode='a', header=False, index=False, sep=';')
    
    return jsonify({'status': 'success', 'message': 'Data saved successfully'})

# --- Endpoint: Admin CSV Export ---
@app.route('/api/export', methods=['GET'])
@require_admin
def export_csv():
    if not os.path.exists(DATA_FILE):
        return jsonify({'error': 'No data available'}), 404
    return send_file(DATA_FILE, mimetype='text/csv', as_attachment=True, download_name='submissions.csv')

# --- Endpoint: AI Chat about Vignette ---
@app.route('/api/chat', methods=['POST'])
def vignette_chat():
    data = request.json
    vignette = data.get('vignette')
    user_message = data.get('message')
    user_id = data.get('user_id', 'anonymous')
    
    if not vignette or not user_message:
        return jsonify({'error': 'Both vignette and message are required'}), 400
    
    # Log the chat interaction
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'chat',
        'page': 'chat',
        'action': 'send_message',
        'details': f'User message: {user_message[:100]}...' if len(user_message) > 100 else f'User message: {user_message}',
        'session_data': f'vignette_length: {len(vignette)}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Use configured AI service for the chat
        prompt = f"""Here is the vignette we're discussing:
        "{vignette}"
        
        Student's question/comment: {user_message}
        
        Please provide a helpful, educational response following the guidelines above."""
        
        result = make_ai_call(prompt, CHAT_SYSTEM_PROMPT)
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'chat',
            'page': 'chat',
            'action': 'ai_response',
            'details': f'AI response: {result[:100]}...' if len(result) > 100 else f'AI response: {result}',
            'session_data': 'ai_service: google'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'response': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Chat API Error: {str(e)}")  # Add logging
        # Return a fallback response instead of error
        fallback_response = f"""Thank you for your question about the vignette. I can see you're interested in discussing: "{user_message}"

This vignette presents an interesting academic scenario. Here are some points to consider:

1. **Student Background**: The scenario involves a student with specific characteristics and circumstances.
2. **Support Strategy**: Consider how the support approach might impact the student's success.
3. **Outcomes**: Think about what factors might have contributed to the results.

What specific aspect of this scenario would you like to explore further? For example:
- The effectiveness of the support method used
- How the student's background might influence their learning
- Alternative approaches that could have been considered

I'm here to help you think through these educational scenarios!"""
        
        # Log the fallback response
        fallback_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'chat',
            'page': 'chat',
            'action': 'fallback_response',
            'details': 'AI API failed, fallback response provided',
            'session_data': f'error: {str(e)}'
        }
        
        df_fallback = pd.DataFrame([fallback_interaction])
        df_fallback.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Student Bias Analysis (after 10+ interactions) ---
@app.route('/api/student-bias', methods=['POST'])
def student_bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    user_id = data.get('user_id', 'anonymous')
    
    if not vignette:
        return jsonify({'error': 'Vignette required'}), 400
    
    # Check if user has enough interactions (10+)
    interactions_file = 'user_interactions.csv'
    if os.path.exists(interactions_file):
        try:
            df = pd.read_csv(interactions_file, sep=';')
            user_chat_count = len(df[(df['user_id'] == user_id) & (df['action'] == 'send_message')])
            
            if user_chat_count < 5:
                return jsonify({'error': f'Need at least 5 chat interactions. You have {user_chat_count}.'}), 403
        except:
            return jsonify({'error': 'Unable to verify interaction count'}), 500
    else:
        return jsonify({'error': 'No interaction history found'}), 404
    
    # Log the bias analysis request
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'bias_analysis',
        'page': 'chat',
        'action': 'request_bias_analysis',
        'details': 'Student requested bias analysis of their vignette',
        'session_data': f'vignette_length: {len(vignette)}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Use configured AI service for bias analysis
        prompt = f"""Vignette to analyze:
        {vignette}
        
        Please provide your bias analysis following the guidelines above. This analysis is for educational purposes to help the student understand potential biases in academic scenarios."""
        
        result = make_ai_call(prompt, BIAS_ANALYSIS_SYSTEM_PROMPT)
        
        # Log the bias analysis response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'bias_analysis',
            'page': 'chat',
            'action': 'bias_analysis_response',
            'details': f'Bias analysis provided: {result[:100]}...' if len(result) > 100 else f'Bias analysis: {result}',
            'session_data': 'ai_service: google'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'bias_analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Student Bias Analysis Error: {str(e)}")
        fallback_analysis = """I apologize, but I'm unable to perform the bias analysis at this time due to a technical issue. 

However, here are some general questions you can consider when analyzing your vignette for potential bias:

1. **Gender Bias**: Does the scenario make assumptions based on gender or pronouns?
2. **Cultural Bias**: Are there stereotypes related to nationality or cultural background?
3. **Academic Field Bias**: Does the scenario reflect stereotypes about certain fields of study?
4. **Performance Bias**: Are the expectations and outcomes influenced by demographic factors?
5. **Support Bias**: Is the type of support offered influenced by student characteristics?

Consider discussing these aspects with your instructor or peers for a more comprehensive analysis."""
        
        return jsonify({'bias_analysis': fallback_analysis, 'status': 'success'})

# --- Endpoint: Prompt Engineering Assistant ---
@app.route('/api/prompt-engineering', methods=['POST'])
def prompt_engineering():
    data = request.json
    user_message = data.get('message')
    question_count = data.get('question_count', 0)
    prompt_data = data.get('prompt_data', {})
    user_id = data.get('user_id', 'anonymous')
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    # Log the prompt engineering interaction
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'prompt_engineering',
        'page': 'prompt_helper',
        'action': 'send_message',
        'details': f'User message: {user_message[:100]}...' if len(user_message) > 100 else f'User message: {user_message}',
        'session_data': f'question_count: {question_count}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Use Google AI for prompt engineering assistance
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load system prompt from file
        try:
            with open('prompt-helper-system-prompt.txt', 'r') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback system prompt if file not found
            system_prompt = """You are an expert prompt engineering assistant specializing in data generation and analysis tasks. Your job is to help users refine their AI prompts using the PCTFT Framework through a guided conversation of maximum 7 questions.

PCTFT FRAMEWORK:
- **Persona**: Who should the AI be? (data scientist, researcher, analyst, etc.)
- **Context**: Background information and constraints
- **Task**: Specific action to perform
- **Format**: Output structure (CSV, JSON, specific data schema, etc.)
- **Target**: Intended audience and use case

IMPORTANT RULES:
1. Start by analyzing their initial prompt (even if rough/incomplete)
2. Ask ONE question at a time to refine each PCTFT element
3. Maximum 7 questions total
4. Be conversational, helpful, AND provide proactive feedback
5. Comment on their choices and suggest improvements
6. Focus on improving their existing prompt, not starting from scratch
7. For data generation tasks, automatically suggest appropriate data schemas

Current conversation state:
- Question count: {question_count}
- Current prompt data: {prompt_data}
- User's latest message: {user_message}

If this is the first message (question_count = 0), they're sharing their initial prompt. Analyze it, provide feedback, and ask about the first missing PCTFT element.

If this is question 7 OR you have enough information for all PCTFT elements, generate the final refined prompt with data schema if applicable.
Otherwise, ask the next logical question while providing helpful commentary and suggestions."""

        prompt = system_prompt.format(
            question_count=question_count,
            prompt_data=prompt_data,
            user_message=user_message
        )
        
        response = model.generate_content(prompt)
        result = response.text
        
        # Increment question count
        new_question_count = question_count + 1
        
        # Update prompt data based on the question number
        updated_prompt_data = prompt_data.copy()
        if question_count == 0:
            updated_prompt_data['task'] = user_message
        elif question_count == 1:
            updated_prompt_data['context'] = user_message
        elif question_count == 2:
            updated_prompt_data['audience'] = user_message
        elif question_count == 3:
            updated_prompt_data['format'] = user_message
        elif question_count == 4:
            updated_prompt_data['tone'] = user_message
        elif question_count == 5:
            updated_prompt_data['constraints'] = user_message
        elif question_count == 6:
            updated_prompt_data['examples'] = user_message
        
        # Check if we should generate final prompt
        final_prompt = None
        if new_question_count >= 7 or "final prompt" in result.lower():
            # Let AI craft the final optimized prompt
            prompt_crafting_request = f"""Based on our conversation, please craft a professional, optimized AI prompt that incorporates all the information we've discussed. 

Here's what we've gathered:
- Task: {updated_prompt_data.get('task', 'Not specified')}
- Context: {updated_prompt_data.get('context', 'Not specified')}
- Audience: {updated_prompt_data.get('audience', 'Not specified')}
- Format: {updated_prompt_data.get('format', 'Not specified')}
- Tone: {updated_prompt_data.get('tone', 'Not specified')}
- Constraints: {updated_prompt_data.get('constraints', 'Not specified')}
- Examples/Details: {updated_prompt_data.get('examples', 'Not specified')}

Please create a single, well-crafted prompt that someone can copy and paste into any AI system to get excellent results. The prompt should be:
1. Clear and specific
2. Include all necessary context
3. Specify the desired output format
4. Include any important constraints
5. Be optimized for best AI performance

Return ONLY the final prompt, nothing else."""

            try:
                prompt_response = model.generate_content(prompt_crafting_request)
                final_prompt = prompt_response.text.strip()
            except:
                # Fallback if AI crafting fails
                final_prompt = f"Create a comprehensive {updated_prompt_data.get('task', 'response')} that addresses all the requirements we discussed in our conversation."
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'prompt_engineering',
            'page': 'prompt_helper',
            'action': 'ai_response',
            'details': f'AI response: {result[:100]}...' if len(result) > 100 else f'AI response: {result}',
            'session_data': f'question_count: {new_question_count}, final_prompt: {bool(final_prompt)}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({
            'response': result,
            'question_count': new_question_count,
            'prompt_data': updated_prompt_data,
            'final_prompt': final_prompt,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Prompt Engineering Error: {str(e)}")
        fallback_response = """I apologize, but I'm having trouble processing your request right now. Let me help you with some general prompt engineering guidance:

For creating effective AI prompts, consider including:

1. **Clear Task**: What exactly do you want the AI to do?
2. **Context**: What background information is relevant?
3. **Audience**: Who is this for?
4. **Format**: How should the output be structured?
5. **Tone**: What style or voice should be used?
6. **Constraints**: Any specific requirements or limitations?
7. **Examples**: Any specific examples to guide the AI?

Please try again, and I'll do my best to help you create an amazing prompt!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Prompt Discussion ---
@app.route('/api/prompt-discussion', methods=['POST'])
def prompt_discussion():
    data = request.json
    user_message = data.get('message')
    current_prompt = data.get('current_prompt')
    user_id = data.get('user_id', 'anonymous')
    
    if not user_message or not current_prompt:
        return jsonify({'error': 'Message and current prompt required'}), 400
    
    # Log the prompt discussion interaction
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'prompt_discussion',
        'page': 'prompt_helper',
        'action': 'send_discussion_message',
        'details': f'User message: {user_message[:100]}...' if len(user_message) > 100 else f'User message: {user_message}',
        'session_data': f'prompt_length: {len(current_prompt)}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Use Google AI for prompt discussion
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create system prompt for prompt discussion
        discussion_prompt = f"""You are an expert prompt engineering consultant. A user has created a prompt and wants to discuss it with you. Your job is to help them refine, understand, or modify their prompt based on their questions or requests.

CURRENT PROMPT:
{current_prompt}

USER'S MESSAGE/QUESTION:
{user_message}

INSTRUCTIONS:
1. Analyze their question/request carefully
2. Provide helpful, specific advice about their prompt
3. If they ask for modifications, suggest specific changes
4. If they want explanations, explain the reasoning behind prompt elements
5. If they want alternatives, suggest different approaches
6. Be conversational and educational
7. If you suggest a modified prompt, provide the complete new version

IMPORTANT: If you provide a modified/updated prompt, clearly indicate it as "UPDATED PROMPT:" followed by the complete new prompt text.

Respond helpfully to their question about the prompt."""

        response = model.generate_content(discussion_prompt)
        result = response.text
        
        # Check if there's an updated prompt in the response
        updated_prompt = None
        if "UPDATED PROMPT:" in result:
            # Extract the updated prompt
            parts = result.split("UPDATED PROMPT:")
            if len(parts) > 1:
                updated_prompt = parts[1].strip()
                # Remove the updated prompt from the main response to avoid duplication
                result = parts[0].strip()
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'prompt_discussion',
            'page': 'prompt_helper',
            'action': 'ai_discussion_response',
            'details': f'AI response: {result[:100]}...' if len(result) > 100 else f'AI response: {result}',
            'session_data': f'updated_prompt: {bool(updated_prompt)}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        response_data = {
            'response': result,
            'status': 'success'
        }
        
        if updated_prompt:
            response_data['updated_prompt'] = updated_prompt
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Prompt Discussion Error: {str(e)}")
        fallback_response = """I apologize, but I'm having trouble processing your request right now. Here are some general tips for prompt discussion:

**Common Questions About Prompts:**
- **"Make it shorter"** - I can help condense your prompt while keeping key elements
- **"Make it more specific"** - I can add more detailed instructions and constraints
- **"Explain why you included X"** - I can explain the reasoning behind specific prompt elements
- **"How would this work with different AI systems?"** - I can suggest adaptations for different platforms
- **"What if I want different output?"** - I can modify the format or style requirements

Please try your question again, and I'll do my best to help you improve your prompt!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Data Analysis ---
@app.route('/api/analyze-data', methods=['POST'])
def analyze_data():
    data = request.json
    data_content = data.get('data')
    data_type = data.get('data_type', 'text')
    user_id = data.get('user_id', 'anonymous')
    
    if not data_content:
        return jsonify({'error': 'Data content required'}), 400
    
    # Log the data analysis request
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'data_analysis',
        'page': 'data_analyzer',
        'action': 'analyze_data',
        'details': f'Data analysis requested: {data_type}',
        'session_data': f'data_length: {len(str(data_content))}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Use Google AI for data analysis
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create analysis prompt based on data type
        if data_type == 'image':
            analysis_prompt = f"""You are an educational researcher analyzing visual data. Please provide a focused, short analysis of this image from an educational research perspective.

Focus on:
- What the image shows (content description)
- Educational relevance or implications
- Key patterns or insights visible
- Research applications or potential uses

Keep your analysis concise (2-3 paragraphs maximum) and educational in nature.

Image data: {data_content}"""
        
        elif data_type == 'csv':
            analysis_prompt = f"""You are an educational researcher analyzing CSV data. Please provide a focused, short analysis of this dataset from an educational research perspective.

Focus on:
- Data structure and variables
- Key patterns, trends, or outliers
- Statistical insights (means, distributions, correlations)
- Educational implications
- Potential research questions this data could answer

Keep your analysis concise (2-3 paragraphs maximum) and educational in nature.

CSV Data:
{data_content}"""
        
        elif data_type == 'json':
            analysis_prompt = f"""You are an educational researcher analyzing JSON data. Please provide a focused, short analysis of this dataset from an educational research perspective.

Focus on:
- Data structure and key fields
- Patterns in the data
- Educational insights or implications
- Potential research applications

Keep your analysis concise (2-3 paragraphs maximum) and educational in nature.

JSON Data:
{data_content}"""
        
        else:  # text or other
            analysis_prompt = f"""You are an educational researcher analyzing text data. Please provide a focused, short analysis of this content from an educational research perspective.

Focus on:
- Main themes or topics
- Educational relevance
- Key insights or patterns
- Research implications
- Potential applications in educational settings

Keep your analysis concise (2-3 paragraphs maximum) and educational in nature.

Text Data:
{data_content}"""
        
        response = model.generate_content(analysis_prompt)
        result = response.text
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'data_analysis',
            'page': 'data_analyzer',
            'action': 'analysis_complete',
            'details': f'Analysis provided for {data_type} data',
            'session_data': f'analysis_length: {len(result)}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Data Analysis Error: {str(e)}")
        
        # Provide fallback analysis based on data type
        if data_type == 'csv':
            fallback_analysis = """I apologize, but I'm having trouble analyzing your CSV data right now. Here's some general guidance for CSV data analysis:

**Key Areas to Examine:**
- **Data Quality**: Check for missing values, outliers, or inconsistencies
- **Descriptive Statistics**: Calculate means, medians, standard deviations for numerical columns
- **Patterns**: Look for trends, correlations between variables, or groupings
- **Educational Insights**: Consider how this data relates to learning outcomes, student performance, or educational interventions

For a more detailed analysis, try uploading a smaller sample or checking the data format."""
        
        elif data_type == 'image':
            fallback_analysis = """I apologize, but I'm having trouble analyzing your image right now. Here's some general guidance for image analysis in educational research:

**Key Areas to Consider:**
- **Content Analysis**: What educational materials, settings, or activities are shown?
- **Visual Elements**: Charts, graphs, text, or educational tools visible
- **Context**: Classroom environment, learning materials, or student work
- **Research Applications**: How this visual data could support educational research

Please try uploading a smaller image file or a different format."""
        
        else:
            fallback_analysis = """I apologize, but I'm having trouble analyzing your data right now. Here's some general guidance for data analysis in educational research:

**Key Areas to Examine:**
- **Content Themes**: What are the main topics or concepts?
- **Patterns**: Are there recurring elements or trends?
- **Educational Relevance**: How does this relate to learning, teaching, or educational outcomes?
- **Research Potential**: What questions could this data help answer?

Please try with a smaller data sample or check the format."""
        
        return jsonify({'analysis': fallback_analysis, 'status': 'success'})

# --- Endpoint: Data Interpretation ---
@app.route('/api/interpret-data', methods=['POST'])
def interpret_data():
    data = request.json
    data_content = data.get('data')
    data_type = data.get('data_type', 'text')
    research_context = data.get('research_context', '')
    analysis_type = data.get('analysis_type', '')
    target_insights = data.get('target_insights', '')
    audience_level = data.get('audience_level', 'undergraduate')
    user_id = data.get('user_id', 'anonymous')
    
    # Get AI settings from request
    ai_service = data.get('ai_service')
    ai_model = data.get('ai_model')
    user_api_key = data.get('user_api_key')
    
    if not data_content:
        return jsonify({'error': 'Data content required'}), 400
    
    # Log the data interpretation request
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'data_interpretation',
        'page': 'data_interpreter',
        'action': 'interpret_data',
        'details': f'Data interpretation requested: {analysis_type}',
        'session_data': f'data_length: {len(str(data_content))}, audience: {audience_level}, ai_service: {ai_service}, ai_model: {ai_model}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Load system prompt from file
        try:
            with open('interpret-data-system-prompt.txt', 'r') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback system prompt if file not found
            system_prompt = """You are an expert data interpreter specializing in educational research and statistical analysis. Your role is to interpret various types of data outputs, statistical results, and analytical visualizations from an educational research perspective.

Provide interpretations that include:
1. Statistical Interpretation: What the numbers/results mean
2. Educational Implications: What this means for learning/teaching
3. Practical Applications: Actionable insights
4. Limitations & Considerations: Important caveats
5. Recommendations: Next steps or applications

Always tailor your interpretation to the educational research perspective and the specified audience level."""
        
        # Create comprehensive interpretation prompt
        interpretation_prompt = f"""INTERPRETATION REQUEST:

Research Context: {research_context if research_context else 'General educational research context'}

Analysis Type: {analysis_type if analysis_type else 'General statistical analysis'}

Target Insights: {target_insights if target_insights else 'General interpretation and educational implications'}

Audience Level: {audience_level}

Data Type: {data_type}

Data to Interpret:
{data_content}

Please provide a comprehensive interpretation following the framework outlined in the system prompt. Focus on the educational research perspective and tailor the complexity to the specified audience level."""
        
        # Use the specified AI service and model
        result = make_ai_call(
            interpretation_prompt, 
            system_prompt, 
            service=ai_service, 
            model=ai_model, 
            user_api_key=user_api_key
        )
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'data_interpretation',
            'page': 'data_interpreter',
            'action': 'interpretation_complete',
            'details': f'Interpretation provided for {analysis_type} analysis using {ai_service}/{ai_model}',
            'session_data': f'interpretation_length: {len(result)}, ai_service: {ai_service}, ai_model: {ai_model}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'analysis': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Data Interpretation Error: {str(e)}")
        
        # Provide fallback interpretation based on analysis type
        if analysis_type == 'statistical_test':
            fallback_analysis = """I apologize, but I'm having trouble interpreting your statistical test results right now. Here's some general guidance for interpreting statistical tests in educational research:

**Key Elements to Consider:**
- **Statistical Significance**: Look at p-values (typically p < 0.05 indicates significance)
- **Effect Size**: Consider practical significance, not just statistical significance
- **Confidence Intervals**: These provide a range of plausible values
- **Educational Implications**: What do these results mean for teaching and learning?

For a more detailed interpretation, please try again or consult with a statistician."""
        
        elif analysis_type == 'network_analysis':
            fallback_analysis = """I apologize, but I'm having trouble interpreting your network analysis right now. Here's some general guidance for network analysis in educational research:

**Key Network Metrics:**
- **Centrality Measures**: Who are the key players in the network?
- **Clustering**: Are there distinct groups or communities?
- **Density**: How connected is the network overall?
- **Educational Applications**: How do these patterns relate to learning, collaboration, or communication?

For a more detailed interpretation, please try again with a smaller dataset."""
        
        else:
            fallback_analysis = """I apologize, but I'm having trouble interpreting your data right now. Here's some general guidance for data interpretation in educational research:

**General Interpretation Framework:**
- **Descriptive Summary**: What does the data show at face value?
- **Patterns and Trends**: What patterns emerge from the analysis?
- **Educational Significance**: How do these findings relate to learning and teaching?
- **Practical Implications**: What actions might educators take based on these results?
- **Limitations**: What are the constraints and caveats of this analysis?

Please try again with a smaller dataset or check the format."""
        
        return jsonify({'analysis': fallback_analysis, 'status': 'success'})

# --- Endpoint: Interactive Data Interpretation Chat ---
@app.route('/api/interpret-chat', methods=['POST'])
def interpret_chat():
    data = request.json
    user_message = data.get('message')
    current_analysis = data.get('current_analysis')
    research_context = data.get('research_context', '')
    analysis_type = data.get('analysis_type', '')
    target_insights = data.get('target_insights', '')
    audience_level = data.get('audience_level', 'undergraduate')
    user_id = data.get('user_id', 'anonymous')
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    # Log the chat interaction
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'interpretation_chat',
        'page': 'data_interpreter',
        'action': 'send_chat_message',
        'details': f'User message: {user_message[:100]}...' if len(user_message) > 100 else f'User message: {user_message}',
        'session_data': f'analysis_type: {analysis_type}, audience: {audience_level}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Create chat prompt for data interpretation discussion
        chat_prompt = f"""You are an expert data interpreter engaged in an interactive discussion about a statistical analysis. Your role is to help the user understand, refine, and explore their data interpretation through conversation.

CURRENT ANALYSIS CONTEXT:
Research Context: {research_context if research_context else 'General educational research'}
Analysis Type: {analysis_type if analysis_type else 'General statistical analysis'}
Target Insights: {target_insights if target_insights else 'General interpretation'}
Audience Level: {audience_level}

CURRENT ANALYSIS:
{current_analysis if current_analysis else 'No analysis provided yet'}

USER'S QUESTION/REQUEST:
{user_message}

INSTRUCTIONS:
1. Respond to the user's specific question or request about the analysis
2. Provide educational explanations appropriate for their audience level
3. If they ask for clarifications, explain statistical concepts clearly
4. If they want to explore implications, discuss practical applications
5. If they request modifications to the analysis, provide an updated interpretation
6. Be conversational, helpful, and educational
7. Encourage critical thinking about the results

IMPORTANT: If you provide a significantly updated or refined analysis based on their request, clearly indicate it as "UPDATED ANALYSIS:" followed by the complete new interpretation.

Focus on being helpful, educational, and responsive to their specific needs while maintaining statistical accuracy."""

        result = make_ai_call(chat_prompt)
        
        # Check if there's an updated analysis in the response
        updated_analysis = None
        if "UPDATED ANALYSIS:" in result:
            # Extract the updated analysis
            parts = result.split("UPDATED ANALYSIS:")
            if len(parts) > 1:
                updated_analysis = parts[1].strip()
                # Remove the updated analysis from the main response to avoid duplication
                result = parts[0].strip()
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'interpretation_chat',
            'page': 'data_interpreter',
            'action': 'ai_chat_response',
            'details': f'AI response: {result[:100]}...' if len(result) > 100 else f'AI response: {result}',
            'session_data': f'updated_analysis: {bool(updated_analysis)}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        response_data = {
            'response': result,
            'status': 'success'
        }
        
        if updated_analysis:
            response_data['updated_analysis'] = updated_analysis
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Interpretation Chat Error: {str(e)}")
        fallback_response = """I apologize, but I'm having trouble processing your question right now. Here are some ways I can help you discuss your data interpretation:

**Common Discussion Topics:**
- **"What does this p-value mean?"** - I can explain statistical significance in practical terms
- **"Is this effect size meaningful?"** - I can discuss practical vs statistical significance
- **"What are the limitations?"** - I can help identify potential issues with the analysis
- **"How do I explain this to others?"** - I can help you communicate results clearly
- **"What should I do next?"** - I can suggest follow-up analyses or actions

Please try your question again, and I'll do my best to help you understand and refine your data interpretation!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: Educational Chatbot ---
@app.route('/api/educational-chat', methods=['POST'])
def educational_chat():
    data = request.json
    user_message = data.get('message')
    system_prompt = data.get('system_prompt')
    chat_history = data.get('chat_history', [])
    user_id = data.get('user_id', 'anonymous')
    config = data.get('config', {})
    
    # Get AI service info if custom
    ai_service = data.get('ai_service')
    user_api_key = data.get('user_api_key')
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    if not system_prompt:
        return jsonify({'error': 'System prompt required'}), 400
    
    # Log the educational chat interaction
    interaction_data = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'user_id': user_id,
        'interaction_type': 'educational_chat',
        'page': 'chatbot_interface',
        'action': 'send_message',
        'details': f'User message: {user_message[:100]}...' if len(user_message) > 100 else f'User message: {user_message}',
        'session_data': f'model_type: {config.get("modelType", "unknown")}, subject: {config.get("coreSubject", "")[:50]}'
    }
    
    df_interaction = pd.DataFrame([interaction_data])
    interactions_file = 'user_interactions.csv'
    if not os.path.exists(interactions_file):
        df_interaction.to_csv(interactions_file, index=False, sep=';')
    else:
        df_interaction.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
    
    try:
        # Determine AI service and model
        if config.get('modelType') == 'custom' and ai_service and user_api_key:
            # Use custom AI service
            service = ai_service
            api_key = user_api_key
            # Use default model for the service
            model = DEFAULT_OPENAI_MODEL if service == 'openai' else DEFAULT_GOOGLE_MODEL
        else:
            # Use system default
            service = DEFAULT_AI_SERVICE
            api_key = None
            model = DEFAULT_OPENAI_MODEL if service == 'openai' else DEFAULT_GOOGLE_MODEL
        
        # Create conversation context from chat history
        conversation_context = ""
        if chat_history:
            recent_history = chat_history[-6:]  # Last 6 messages for context
            for msg in recent_history:
                if msg.get('type') == 'user':
                    conversation_context += f"Student: {msg.get('content', '')}\n"
                elif msg.get('type') == 'bot':
                    conversation_context += f"Assistant: {msg.get('content', '')}\n"
        
        # Create full prompt with context
        full_prompt = f"""Previous conversation:
{conversation_context}

Current student message: {user_message}

Please respond as the educational assistant following your persona and guidelines."""
        
        # Make AI call
        result = make_ai_call(
            full_prompt,
            system_prompt,
            service=service,
            model=model,
            user_api_key=api_key
        )
        
        # Log the AI response
        response_interaction = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'user_id': user_id,
            'interaction_type': 'educational_chat',
            'page': 'chatbot_interface',
            'action': 'ai_response',
            'details': f'AI response: {result[:100]}...' if len(result) > 100 else f'AI response: {result}',
            'session_data': f'service: {service}, model: {model}'
        }
        
        df_response = pd.DataFrame([response_interaction])
        df_response.to_csv(interactions_file, mode='a', header=False, index=False, sep=';')
        
        return jsonify({'response': result, 'status': 'success'})
        
    except Exception as e:
        print(f"Educational Chat Error: {str(e)}")
        
        # Provide educational fallback response
        fallback_response = f"""I understand you're asking about: "{user_message}"

I apologize, but I'm having a technical difficulty right now. However, I'd still like to help you learn! Here are some ways we can approach your question:

1. **Break it down**: Can you tell me what specific part you'd like to understand better?
2. **Context**: What have you already learned about this topic?
3. **Application**: How do you think this might be used in real situations?

Please try asking your question again, and I'll do my best to help you understand the concept step by step!"""
        
        return jsonify({'response': fallback_response, 'status': 'success'})

# --- Endpoint: AI Bias Analysis ---
@app.route('/api/bias', methods=['POST'])
@require_admin
def bias_analysis():
    data = request.json
    vignette = data.get('vignette')
    api_key = data.get('api_key')
    service = data.get('service', AI_SERVICE)
    
    # Only return mock for explicit test requests
    if api_key == 'test' or api_key == 'TEST':
        # Return mock analysis for testing
        mock_analysis = f"""MOCK BIAS ANALYSIS:
        
Vignette analyzed: "{vignette[:100]}{'...' if len(vignette) > 100 else ''}"

Potential bias indicators found:
- Gender representation: Check pronoun usage
- Nationality bias: Review nationality selection
- Academic field stereotypes: Examine field of study choices
- Performance assumptions: Analyze progress descriptors

Recommendation: This is a test response. For real bias analysis, provide a valid API key."""
        
        return jsonify({'bias_analysis': mock_analysis})
    
    if not vignette:
        return jsonify({'error': 'Vignette required'}), 400
    
    try:
        if service == 'google' or not api_key:
            # Use Google AI (embedded API key)
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""{BIAS_ANALYSIS_SYSTEM_PROMPT}
            
            Vignette to analyze:
            {vignette}
            
            Please provide your bias analysis following the guidelines above."""
            
            response = model.generate_content(prompt)
            result = response.text
            return jsonify({'bias_analysis': result, 'service': 'google'})
            
        elif service == 'openai':
            # Use OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "system", "content": "You are an expert in bias detection for academic vignettes."},
                    {"role": "user", "content": f"Analyze the following vignette for bias and provide a brief explanation: {vignette}"}
                ]
            )
            result = response.choices[0].message.content
            return jsonify({'bias_analysis': result, 'service': 'openai'})
            
        else:
            return jsonify({'error': 'Invalid service specified'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Backend will be available at: http://localhost:5001")
    print("Test page: http://localhost:5001/test-connection.html")
    print("Admin panel: http://localhost:5001/admin.html")
    app.run(debug=True, host='0.0.0.0', port=5001)
