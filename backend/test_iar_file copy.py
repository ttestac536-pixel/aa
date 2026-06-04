#!/usr/bin/env python3
"""
Simple script to test IAR generation
"""

import os
import sys
import zipfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_iar_generation():
    """Test IAR code generation"""
    
    from ai_generator.llm_agent import OICLLMAgent
    
    print("Initializing OIC LLM Agent...")
    agent = OICLLMAgent()
    
    # Test instruction
    instructions = """
    Create an integration that:
    1. Reads a CSV file from SFTP server
    2. Parses journal data with columns: journal_name, period, account_code, debit_amount, credit_amount, description, currency
    3. Validates that either debit OR credit is populated (not both, not neither)
    4. Transforms the data to Oracle GL Journal Import format
    5. Inserts into Oracle Financials GL_INTERFACE table
    6. Logs success/failure
    7. Handles errors and retries with exponential backoff
    """
    
    print("=" * 80)
    print("Testing OIC IAR Code Generation")
    print("=" * 80)
    print(f"\nInstructions:\n{instructions}\n")
    print("Generating IAR code...")
    print("-" * 80)
    
    success, result = agent.generate_integration_code(instructions)
    
    if success:
        print("✅ IAR Generated Successfully!\n")

        req       = result['requirements']
        filename  = result['filename']
        iar_bytes = result['iar_bytes']

        # ── Write the IAR (it's a ZIP — must use 'wb') ──────────────────
        with open(filename, 'wb') as f:
            f.write(iar_bytes)

        # ── Summary ─────────────────────────────────────────────────────
        print(f"  IAR file   : {filename}")
        print(f"  File size  : {len(iar_bytes):,} bytes")
        print(f"  Integration: {req['integration_name']}")
        print(f"  Version    : {req['version']}")
        print(f"  Source     : {req['source_type']} @ {req['source_host']}:{req['source_port']}")
        print(f"  Target     : {req['target_type']} @ {req['target_host']}:{req['target_port']}")
        print(f"  Mappings   : {len(req['field_mappings'])} fields")
        print(f"  Timestamp  : {result['timestamp']}")

        # ── Verify ZIP contents ──────────────────────────────────────────
        print("\nIAR contents (ZIP):")
        print("-" * 80)
        with zipfile.ZipFile(filename, 'r') as zf:
            for entry in zf.namelist():
                info = zf.getinfo(entry)
                print(f"  {entry:<60}  {info.file_size:>8,} bytes")

        # ── Show IntegrationDefinition.xml preview ───────────────────────
        print("\nIntegrationDefinition.xml preview (first 1500 chars):")
        print("-" * 80)
        with zipfile.ZipFile(filename, 'r') as zf:
            names = zf.namelist()
            defn  = next((n for n in names if n.endswith('IntegrationDefinition.xml')), None)
            if defn:
                xml_preview = zf.read(defn).decode('utf-8')
                print(xml_preview[:1500])
                if len(xml_preview) > 1500:
                    print(f"\n... ({len(xml_preview) - 1500} more characters)")
            else:
                print("  (IntegrationDefinition.xml not found in archive)")
        print("-" * 80)

        return True

    else:
        print("❌ Generation Failed!")
        print(f"\nError    : {result.get('error')}")
        if 'traceback' in result:
            print(f"\nTraceback:\n{result['traceback']}")
        return False


if __name__ == '__main__':
    try:
        success = test_iar_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)