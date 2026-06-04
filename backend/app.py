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
    """Generate OIC IAR integration code from user instructions"""
    data = request.get_json()
    instructions = data.get('instructions', '').strip()

    if not instructions:
        return jsonify({'error': 'Instructions required'}), 400

    try:
        agent = OICLLMAgent()
        success, result = agent.generate_integration_code(instructions)
        # agent = OICLLMAgent(template_iar_path="CSVSFTPTOORACLEGLJOURNAL_01000000.iar")
        # success, result = agent.generate_integration_code(instructions)

        if not success:
            return jsonify(result), 400

        # Save IAR file (binary)
        iar_bytes = result['iar_bytes']
        filename = result['filename']
        filepath = os.path.join('generated_iar', filename)

        with open(filepath, 'wb') as f:
            f.write(iar_bytes)

        return jsonify({
            'success': True,
            'message': 'IAR code generated successfully',
            'iar_filename': filename,
            'iar_filepath': filepath,
            'timestamp': result['timestamp'],
            'model': result['model'],
            'requirements': result['requirements']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== Chat Conversation ====================

@app.route('/api/chat', methods=['POST'])
def chat_message():
    """Chat-based conversation to gather integration requirements"""
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
    """Deploy generated IAR file to OIC instance"""
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