from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid
from ai_generator.llm_agent import OICLLMAgent
from oic_handler.oic_deployer import OICDeployer

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs('uploads', exist_ok=True)
os.makedirs('generated_iar', exist_ok=True)

# Store sessions
sessions = {}

# ==================== Generate IAR Code ====================

@app.route('/api/generate-iar', methods=['POST'])
def generate_iar_code():
    """
    Generate OIC IAR integration code from user instructions
    
    Request body:
    {
        "instructions": "Create SFTP to Oracle GL integration for journal data..."
    }
    
    Response:
    {
        "success": true,
        "iar_code": "<?xml version=...",
        "iar_filename": "integration_20240115_120530.iar",
        "timestamp": "2024-01-15T12:05:30..."
    }
    """
    
    data = request.get_json()
    instructions = data.get('instructions', '').strip()

    if not instructions:
        return jsonify({'error': 'Instructions required'}), 400

    try:
        agent = OICLLMAgent()
        success, result = agent.generate_integration_code(instructions)

        if not success:
            return jsonify(result), 400

        # Save IAR file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"integration_{timestamp}.iar"
        filepath = os.path.join('generated_iar', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result['iar_code'])

        return jsonify({
            'success': True,
            'message': 'IAR code generated successfully',
            'iar_code': result['iar_code'],
            'iar_filename': filename,
            'iar_filepath': filepath,
            'timestamp': result['timestamp']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Refine IAR Code ====================

@app.route('/api/refine-iar', methods=['POST'])
def refine_iar_code():
    """
    Refine existing IAR code based on feedback
    
    Request body:
    {
        "iar_code": "<?xml version=...",
        "feedback": "Add retry logic..."
    }
    """
    
    data = request.get_json()
    iar_code = data.get('iar_code', '').strip()
    feedback = data.get('feedback', '').strip()

    if not iar_code or not feedback:
        return jsonify({'error': 'IAR code and feedback required'}), 400

    try:
        agent = OICLLMAgent()
        success, result = agent.refine_integration_code(iar_code, feedback)

        if not success:
            return jsonify(result), 400

        # Save refined IAR file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"integration_refined_{timestamp}.iar"
        filepath = os.path.join('generated_iar', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result['iar_code'])

        return jsonify({
            'success': True,
            'message': 'IAR code refined successfully',
            'iar_code': result['iar_code'],
            'iar_filename': filename,
            'iar_filepath': filepath,
            'timestamp': result['timestamp']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Chat Conversation ====================

@app.route('/api/chat', methods=['POST'])
def chat_message():
    """
    Chat-based conversation to gather integration requirements
    
    Request body:
    {
        "session_id": "uuid",
        "message": "I want to create..."
    }
    """
    
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message', '').strip()

    if not session_id or not message:
        return jsonify({'error': 'session_id and message required'}), 400

    # Initialize session if not exists
    if session_id not in sessions:
        sessions[session_id] = {
            'history': [],
            'created_at': datetime.now().isoformat()
        }

    try:
        session = sessions[session_id]
        agent = OICLLMAgent()

        response, updated_history = agent.generate_integration_with_chat(
            message,
            session['history']
        )

        session['history'] = updated_history

        return jsonify({
            'success': True,
            'response': response,
            'session_id': session_id
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Get OIC Instances ====================

@app.route('/api/oic-instances', methods=['GET'])
def get_oic_instances():
    """Get available OIC instances for deployment"""
    try:
        deployer = OICDeployer()
        instances = deployer.get_available_instances()
        
        return jsonify({
            'success': True,
            'instances': instances,
            'count': len(instances)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Deploy IAR to OIC ====================

@app.route('/api/deploy-iar', methods=['POST'])
def deploy_iar_to_oic():
    """
    Deploy generated IAR file to OIC instance
    
    Request body:
    {
        "iar_filepath": "path/to/integration.iar",
        "oic_instance": "prod",
        "integration_name": "MyIntegration_v1"
    }
    """
    
    data = request.get_json()
    iar_filepath = data.get('iar_filepath')
    oic_instance = data.get('oic_instance')
    integration_name = data.get('integration_name', 'Integration')

    if not iar_filepath or not oic_instance:
        return jsonify({'error': 'IAR filepath and OIC instance required'}), 400

    try:
        deployer = OICDeployer()
        success, result = deployer.deploy_iar_to_instance(
            iar_filepath,
            oic_instance,
            integration_name
        )

        if not success:
            return jsonify(result), 400

        return jsonify({
            'success': True,
            'message': 'IAR deployed to OIC successfully',
            **result
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Health Check ====================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'Backend running',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)