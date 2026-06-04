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

# ==================== Chat Endpoints ====================

@app.route('/api/chat', methods=['POST'])
def chat_message():
    """Chat endpoint for conversational interaction"""
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')

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

        # Get response from LLM
        response_text, updated_history = agent.generate_integration_with_chat(
            message,
            session['history']
        )

        session['history'] = updated_history

        return jsonify({
            'success': True,
            'response': response_text,
            'session_id': session_id
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            'timestamp': result['timestamp'],
            'model': result['model']
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

# ==================== Test Connection ====================

@app.route('/api/test-connection/<instance_name>', methods=['GET'])
def test_connection(instance_name):
    """Test connection to OIC instance"""
    try:
        deployer = OICDeployer()
        success, message = deployer.test_connection(instance_name)
        
        return jsonify({
            'instance': instance_name,
            'connected': success,
            'message': message
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