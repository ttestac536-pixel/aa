import requests
import os
import json
import base64
from typing import Tuple, Dict
from requests.auth import HTTPBasicAuth

class OICDeployer:
    """
    Deploys generated IAR files to OIC instances
    """

    def __init__(self):
        self.oic_instances = self._parse_oic_instances()

    def _parse_oic_instances(self) -> Dict:
        """Parse OIC instances from environment variables"""
        try:
            instances_json = os.getenv('OIC_INSTANCES', '{}')
            return json.loads(instances_json)
        except:
            return {
                'dev': {
                    'url': 'https://oic-dev.oracle.com',
                    'username': os.getenv('OIC_USERNAME'),
                    'password': os.getenv('OIC_PASSWORD')
                }
            }

    def get_available_instances(self) -> Dict[str, str]:
        """Return available OIC instances"""
        return {
            name: config['url']
            for name, config in self.oic_instances.items()
        }

    def deploy_iar_to_instance(self, iar_filepath: str, instance_name: str, integration_name: str) -> Tuple[bool, Dict]:
        """
        Deploy IAR file to OIC instance
        
        Args:
            iar_filepath: Path to IAR file
            instance_name: OIC instance name (dev, staging, prod)
            integration_name: Name for the integration
            
        Returns:
            Tuple of (success: bool, result: Dict)
        """
        
        if instance_name not in self.oic_instances:
            return False, {'error': f"OIC instance '{instance_name}' not found"}

        config = self.oic_instances[instance_name]
        oic_url = config['url']
        username = config['username']
        password = config['password']

        # Check file exists
        if not os.path.exists(iar_filepath):
            return False, {'error': f'IAR file not found: {iar_filepath}'}

        try:
            # Read IAR file
            with open(iar_filepath, 'rb') as f:
                iar_content = f.read()

            # Prepare headers
            headers = {
                'Content-Type': 'application/octet-stream',
                'X-Integration-Name': integration_name
            }

            # OIC API endpoint
            deploy_url = f"{oic_url}/ic/api/integration/v1/integrations/import"

            # POST to OIC
            response = requests.post(
                deploy_url,
                data=iar_content,
                headers=headers,
                auth=HTTPBasicAuth(username, password),
                timeout=60,
                verify=False
            )

            if response.status_code in [200, 201]:
                response_data = response.json() if response.content else {}
                
                return True, {
                    'status': 'success',
                    'message': 'IAR deployed successfully',
                    'instance': instance_name,
                    'oic_url': oic_url,
                    'integration_name': integration_name,
                    'deployment_response': response_data
                }
            else:
                return False, {
                    'error': f"Deployment failed: {response.status_code}",
                    'details': response.text,
                    'instance': instance_name
                }

        except requests.exceptions.ConnectionError as e:
            return False, {
                'error': f"Cannot connect to OIC: {str(e)}",
                'instance': instance_name
            }
        except Exception as e:
            return False, {
                'error': f"Deployment error: {str(e)}",
                'instance': instance_name
            }

    def test_connection(self, instance_name: str) -> Tuple[bool, str]:
        """Test connection to OIC instance"""
        
        if instance_name not in self.oic_instances:
            return False, f"Instance '{instance_name}' not found"

        config = self.oic_instances[instance_name]
        oic_url = config['url']
        username = config['username']
        password = config['password']

        try:
            response = requests.get(
                f"{oic_url}/ic/api/integration/v1/integrations",
                auth=HTTPBasicAuth(username, password),
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                return True, f"✅ Connected to {instance_name}"
            else:
                return False, f"Connection test failed: {response.status_code}"

        except Exception as e:
            return False, f"Connection error: {str(e)}"