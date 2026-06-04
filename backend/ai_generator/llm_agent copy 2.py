import cohere
import json
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Tuple, Dict, Any
from datetime import datetime


def _normalize_ver(version: str) -> str:
    """Enforce OIC version format: 01.00.0000"""
    parts = (version or "01.00.0000").split('.')
    while len(parts) < 3:
        parts.append('0000')
    return f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2].zfill(4)}"


def _make_integration_definition(name: str, description: str,
                                  version: str, source_conn: str,
                                  target_conn: str,
                                  field_mappings: list = None) -> str:
    """Build IntegrationDefinition.xml"""
    integration_id = name.upper().replace(" ", "_").replace("-", "_")[:50]
    version = _normalize_ver(version)
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    mappings_xml = ""
    for m in (field_mappings or []):
        mappings_xml += (
            f"    <mapping>\n"
            f"      <source>{m.get('source', '')}</source>\n"
            f"      <target>{m.get('target', '')}</target>\n"
            f"      <dataType>{m.get('dataType', 'STRING')}</dataType>\n"
            f"    </mapping>\n"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<integration xmlns="http://xmlns.oracle.com/tip/integration"\n'
        '             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        f'             code="{integration_id}"\n'
        f'             version="{version}"\n'
        '             status="CONFIGURED">\n'
        f'  <code>{integration_id}</code>\n'
        f'  <version>{version}</version>\n'
        f'  <name>{name}</name>\n'
        f'  <description>{description}</description>\n'
        '  <style>MAP_DATA</style>\n'
        f'  <created>{now}</created>\n'
        f'  <modified>{now}</modified>\n'
        '  <endpoints>\n'
        '    <endpoint role="source">\n'
        '      <name>SourceEndpoint</name>\n'
        '      <connection><code>SOURCECONNECTION</code></connection>\n'
        '    </endpoint>\n'
        '    <endpoint role="target">\n'
        '      <name>TargetEndpoint</name>\n'
        '      <connection><code>TARGETCONNECTION</code></connection>\n'
        '    </endpoint>\n'
        '  </endpoints>\n'
        '  <mappings>\n'
        f'{mappings_xml}'
        '  </mappings>\n'
        '</integration>'
    )


def _make_connection_xml(conn_name: str, adapter_type: str,
                          host: str, port: str, extra: dict) -> str:
    """Build connection XML"""
    conn_code = conn_name.upper().replace(' ', '_').replace('-', '_')
    props = "\n".join(
        f'    <property name="{k}">{v}</property>'
        for k, v in extra.items()
    )
    
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<connection xmlns="http://xmlns.oracle.com/tip/connection"\n'
        f'            code="{conn_code}"\n'
        f'            adapterType="{adapter_type.upper()}"\n'
        '            status="CONFIGURED">\n'
        f'  <code>{conn_code}</code>\n'
        f'  <name>{conn_name}</name>\n'
        f'  <adapterType>{adapter_type.upper()}</adapterType>\n'
        '  <properties>\n'
        f'    <property name="host">{host}</property>\n'
        f'    <property name="port">{port}</property>\n'
        f'{props}\n'
        '  </properties>\n'
        '</connection>'
    )


def _make_manifest(integration_id: str, version: str) -> str:
    """Build manifest XML"""
    version = _normalize_ver(version)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<icspackage xmlns="http://xmlns.oracle.com/ics/package">\n'
        '  <integrations>\n'
        '    <integration>\n'
        f'      <code>{integration_id}</code>\n'
        f'      <version>{version}</version>\n'
        '    </integration>\n'
        '  </integrations>\n'
        '</icspackage>'
    )


def _make_project_attributes(integration_id: str, version: str,
                              description: str) -> str:
    """Build project attributes properties file"""
    version = _normalize_ver(version)
    return (
        f"project.name={integration_id}\n"
        f"project.version={version}\n"
        f"project.description={description}\n"
        "project.type=INTEGRATION\n"
        "project.status=CONFIGURED\n"
    )


def _make_integration_attributes(integration_id: str, version: str) -> str:
    """Build integration attributes properties file"""
    version = _normalize_ver(version)
    return (
        f"integration.id={integration_id}\n"
        f"integration.version={version}\n"
        "integration.type=MAP_DATA\n"
        "integration.style=MAP_DATA\n"
        "integration.status=CONFIGURED\n"
    )


def build_iar_zip(integration_def_xml: str,
                  source_conn_xml: str,
                  target_conn_xml: str,
                  integration_id: str,
                  version: str,
                  description: str = "") -> bytes:
    """Build OIC IAR ZIP file"""
    version = _normalize_ver(version)
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        base = f"icspackage/project/{integration_id}/"

        zf.writestr(base + "ics_project_attributes.properties",
                    _make_project_attributes(integration_id, version, description))
        zf.writestr(base + "ics_integration_attributes.properties",
                    _make_integration_attributes(integration_id, version))
        zf.writestr(base + "IntegrationDefinition.xml", integration_def_xml)

        conn_base = base + "resources/connections/"
        zf.writestr(conn_base + "SourceConnection.xml", source_conn_xml)
        zf.writestr(conn_base + "TargetConnection.xml", target_conn_xml)

        zf.writestr("icspackage/icspackage.xml",
                    _make_manifest(integration_id, version))

    return buf.getvalue()


class OICLLMAgent:
    """LLM Agent for generating OIC IAR files"""

    def __init__(self):
        self.api_key = os.getenv('COHERE_API_KEY')
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not set in environment")
        self.client = cohere.ClientV2(api_key=self.api_key)
        self.model = "command-a-plus-05-2026"

    def _extract_text(self, response) -> str:
        """Extract text from Cohere response"""
        try:
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                content = response.message.content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        item_type = (
                            item.type if hasattr(item, 'type')
                            else item.get('type', '') if isinstance(item, dict)
                            else ''
                        )
                        if item_type == 'thinking':
                            continue
                        if hasattr(item, 'text'):
                            parts.append(item.text)
                        elif isinstance(item, dict) and 'text' in item:
                            parts.append(item['text'])
                    return "\n".join(parts)
                if isinstance(content, str):
                    return content
                if hasattr(content, 'text'):
                    return content.text
            if hasattr(response, 'text'):
                return response.text
            return str(response)
        except Exception as e:
            raise ValueError(f"Could not extract text: {e}")

    def _normalize_version(self, raw: str) -> str:
        return _normalize_ver(raw)

    def _extract_requirements(self, user_instructions: str) -> dict:
        """LLM extracts structured requirements as JSON"""
        prompt = f"""You are an OIC integration architect.
Extract integration requirements from the user instructions.
Return ONLY a JSON object — no markdown, no explanation.

JSON format:
{{
  "integration_name": "SFTPtoOracleGL",
  "description": "SFTP CSV to Oracle GL Journal Import",
  "version": "01.00.0000",
  "source_type": "SFTP",
  "source_host": "sftp.example.com",
  "source_port": "22",
  "source_extra": {{"directory": "/incoming", "filename": "*.csv"}},
  "target_type": "ORACLE",
  "target_host": "oracle.example.com",
  "target_port": "1521",
  "target_extra": {{"database": "FINPROD", "schema": "GL"}},
  "field_mappings": [
    {{"source": "journal_name", "target": "JE_BATCH_ID", "dataType": "STRING"}},
    {{"source": "period", "target": "PERIOD_NAME", "dataType": "STRING"}},
    {{"source": "account_code", "target": "CODE_COMBINATION_ID", "dataType": "STRING"}},
    {{"source": "debit_amount", "target": "ENTERED_DR_AMOUNT", "dataType": "DECIMAL"}},
    {{"source": "credit_amount", "target": "ENTERED_CR_AMOUNT", "dataType": "DECIMAL"}},
    {{"source": "description", "target": "DESCRIPTION", "dataType": "STRING"}},
    {{"source": "currency", "target": "CURRENCY_CODE", "dataType": "STRING"}}
  ]
}}

USER INSTRUCTIONS:
{user_instructions}

Output ONLY the JSON object."""

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = self._extract_text(response).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    def generate_integration_code(self,
                                  user_instructions: str
                                  ) -> Tuple[bool, Dict[str, Any]]:
        """Generate OIC IAR ZIP file from user instructions"""
        try:
            print("Step 1/3 — extracting requirements ...")
            req = self._extract_requirements(user_instructions)
            req['version'] = self._normalize_version(req.get('version', '01.00.0000'))
            print(f"  integration: {req['integration_name']} v{req['version']}")
            print(f"  {req['source_type']} → {req['target_type']}")
            print(f"  {len(req.get('field_mappings', []))} field mappings")

            print("Step 2/3 — building IntegrationDefinition.xml ...")
            integration_def_xml = _make_integration_definition(
                name=req['integration_name'],
                description=req['description'],
                version=req['version'],
                source_conn="SOURCECONNECTION",
                target_conn="TARGETCONNECTION",
                field_mappings=req.get('field_mappings', []),
            )

            if req['version'] not in integration_def_xml:
                raise RuntimeError(
                    f"Version {req['version']} missing from IntegrationDefinition.xml"
                )

            print("Step 3/3 — building IAR zip ...")
            source_conn_xml = _make_connection_xml(
                conn_name="SourceConnection",
                adapter_type=req['source_type'],
                host=req['source_host'],
                port=req['source_port'],
                extra=req.get('source_extra', {}),
            )
            target_conn_xml = _make_connection_xml(
                conn_name="TargetConnection",
                adapter_type=req['target_type'],
                host=req['target_host'],
                port=req['target_port'],
                extra=req.get('target_extra', {}),
            )

            integration_id = req['integration_name'].upper().replace(' ', '_').replace('-', '_')
            iar_bytes = build_iar_zip(
                integration_def_xml=integration_def_xml,
                source_conn_xml=source_conn_xml,
                target_conn_xml=target_conn_xml,
                integration_id=integration_id,
                version=req['version'],
                description=req.get('description', ''),
            )

            filename = f"{integration_id}_{req['version'].replace('.', '')}.iar"
            return True, {
                'success': True,
                'filename': filename,
                'iar_bytes': iar_bytes,
                'requirements': req,
                'timestamp': datetime.now().isoformat(),
                'model': self.model,
            }

        except json.JSONDecodeError as e:
            return False, {'error': f'LLM returned invalid JSON: {e}'}
        except Exception as e:
            import traceback
            return False, {
                'error': str(e),
                'traceback': traceback.format_exc()
            }

    def generate_integration_with_chat(self,
                                       user_message: str,
                                       conversation_history: list
                                       ) -> Tuple[str, list]:
        """Chat mode - gather requirements"""
        system_prompt = """You are an OIC expert helping users define integrations.
Ask about: source system, target system, data fields, error handling.
Be conversational. When ready say: "I have all the info! Ready to generate the IAR code!"
"""
        full_prompt = system_prompt + "\nConversation so far:"
        for msg in conversation_history:
            full_prompt += f"\n{msg['role'].upper()}: {msg['content']}"
        full_prompt += f"\nUSER: {user_message}"

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}]
            )
            assistant_msg = self._extract_text(response).strip()
            updated_history = conversation_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_msg},
            ]
            return assistant_msg, updated_history
        except Exception as e:
            return f"Error: {e}", conversation_history