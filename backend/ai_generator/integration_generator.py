import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any
import openai
from xml.dom import minidom

class IntegrationGenerator:
    """
    Uses OpenAI LLM to generate OIC IAR XML files
    Takes CSV structure + Oracle GL target format as input
    Outputs OIC-compatible IAR XML
    """

    def __init__(self, csv_filepath: str = None):
        self.csv_filepath = csv_filepath
        self.csv_data = []
        self.headers = []
        self.llm_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.iar_xml = None

    def read_csv(self) -> bool:
        """Read and parse CSV file to understand structure"""
        if not self.csv_filepath or not os.path.exists(self.csv_filepath):
            return False
        
        try:
            with open(self.csv_filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.headers = reader.fieldnames
                self.csv_data = list(reader)
            return True
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return False

    def get_csv_structure_description(self) -> str:
        """Get description of CSV structure for LLM"""
        headers_str = ", ".join(self.headers) if self.headers else ""
        sample_row = json.dumps(self.csv_data[0], indent=2) if self.csv_data else "{}"
        
        return f"""
CSV File Structure:
- Headers: {headers_str}
- Total Rows: {len(self.csv_data)}
- Sample Row: {sample_row}
"""

    def ask_llm_to_generate_iar_xml(self) -> str:
        """
        Use LLM to generate complete OIC IAR XML structure
        This XML can be directly deployed to OIC via REST API
        """
        csv_structure = self.get_csv_structure_description()
        
        prompt = f"""
You are an Oracle Integration Cloud (OIC) expert. Generate a complete, deployable OIC IAR XML integration file.

{csv_structure}

Target System: Oracle Financials (GL Journal Import)
Target Format: Oracle GL FDBI format

Generate a valid OIC IAR XML that:
1. Defines the SFTP source connection (reads CSV)
2. Defines the Oracle Financials GL connection (target)
3. Maps CSV columns to Oracle GL fields:
   - CSV columns to JE_BATCH_ID, PERIOD_NAME, CODE_COMBINATION_ID, ENTERED_DR_AMOUNT, ENTERED_CR_AMOUNT, DESCRIPTION, CURRENCY_CODE
4. Includes data transformation logic
5. Includes validation rules
6. Includes error handling
7. Is ready to be deployed to OIC

The XML must follow OIC IAR schema standards. Include:
- <?xml version="1.0" encoding="UTF-8"?>
- Integration metadata
- Connection configurations
- Mapping and transformation flows
- Error handlers

Return ONLY the complete, valid XML. No explanations, no markdown, no backticks.
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000
            )
            
            iar_xml = response.choices[0].message.content.strip()
            
            # Clean up if LLM wrapped in markdown
            if iar_xml.startswith('```'):
                iar_xml = '\n'.join(iar_xml.split('\n')[1:-1])
            
            self.iar_xml = iar_xml
            return iar_xml
        except Exception as e:
            print(f"LLM IAR generation error: {e}")
            return self._get_fallback_iar_xml()

    def _get_fallback_iar_xml(self) -> str:
        """Fallback IAR XML if LLM fails"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Integration xmlns="http://xmlns.oracle.com/integration/oic">
    <IntegrationMetadata>
        <Name>JournalImport_{timestamp}</Name>
        <Version>1.0</Version>
        <Description>AI-generated journal data import integration</Description>
        <CreatedDate>{datetime.now().isoformat()}</CreatedDate>
        <LastModifiedDate>{datetime.now().isoformat()}</LastModifiedDate>
    </IntegrationMetadata>
    
    <Connections>
        <Connection>
            <Type>SFTP</Type>
            <Name>SFTP_JournalSource</Name>
            <Description>SFTP connection for journal CSV files</Description>
        </Connection>
        <Connection>
            <Type>OracleFinancials</Type>
            <Name>OracleGL_Target</Name>
            <Description>Oracle Financials GL Journal Import</Description>
        </Connection>
    </Connections>
    
    <IntegrationFlow>
        <Name>JournalImportFlow</Name>
        <Steps>
            <Step>
                <Name>ReadCSVFile</Name>
                <Type>SourceAdapter</Type>
                <Connection>SFTP_JournalSource</Connection>
                <Operation>ReadFile</Operation>
            </Step>
            <Step>
                <Name>TransformData</Name>
                <Type>Mapper</Type>
                <Mappings>
                    <Mapping SourceField="journal_name" TargetField="JE_BATCH_ID"/>
                    <Mapping SourceField="period" TargetField="PERIOD_NAME"/>
                    <Mapping SourceField="account_code" TargetField="CODE_COMBINATION_ID"/>
                    <Mapping SourceField="debit_amount" TargetField="ENTERED_DR_AMOUNT"/>
                    <Mapping SourceField="credit_amount" TargetField="ENTERED_CR_AMOUNT"/>
                    <Mapping SourceField="description" TargetField="DESCRIPTION"/>
                    <Mapping SourceField="currency" TargetField="CURRENCY_CODE"/>
                </Mappings>
            </Step>
            <Step>
                <Name>ValidateData</Name>
                <Type>Validation</Type>
                <Rules>
                    <Rule>Debit or Credit amount required</Rule>
                    <Rule>Description must not be empty</Rule>
                    <Rule>Account code must be valid</Rule>
                </Rules>
            </Step>
            <Step>
                <Name>ImportToOracleGL</Name>
                <Type>TargetAdapter</Type>
                <Connection>OracleGL_Target</Connection>
                <Operation>GLJournalImport</Operation>
            </Step>
        </Steps>
        <ErrorHandling>
            <ErrorHandler>
                <Condition>MappingError</Condition>
                <Action>LogAndContinue</Action>
            </ErrorHandler>
            <ErrorHandler>
                <Condition>ValidationError</Condition>
                <Action>LogAndStop</Action>
            </ErrorHandler>
        </ErrorHandling>
    </IntegrationFlow>
</Integration>
"""

    def generate_iar_file(self, output_filepath: str) -> bool:
        """Save IAR XML file"""
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(self.iar_xml)
            return True
        except Exception as e:
            print(f"Error generating IAR file: {e}")
            return False

    def process(self, output_dir: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Main LLM-based processing pipeline:
        1. Read source CSV
        2. Use LLM to generate OIC IAR XML
        3. Save IAR file
        4. Return file path for REST API deployment
        """
        result = {
            'success': False,
            'integration_id': None,
            'iar_file': None,
            'iar_xml': None,
            'errors': []
        }

        try:
            # Step 1: Read CSV
            print("📖 Reading CSV file...")
            if self.csv_filepath:
                if not self.read_csv():
                    result['errors'].append('Failed to read CSV file')
                    return False, result
            else:
                result['errors'].append('CSV file path required')
                return False, result

            # Step 2: Use LLM to generate IAR XML
            print("🤖 LLM: Generating OIC IAR XML...")
            iar_xml = self.ask_llm_to_generate_iar_xml()
            
            if not iar_xml:
                result['errors'].append('Failed to generate IAR XML from LLM')
                return False, result

            result['iar_xml'] = iar_xml

            # Step 3: Save IAR file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            integration_id = f"integration_{timestamp}"
            iar_filename = f"{integration_id}.iar"
            iar_filepath = os.path.join(output_dir, iar_filename)

            if not self.generate_iar_file(iar_filepath):
                result['errors'].append('Failed to save IAR file')
                return False, result

            result['success'] = True
            result['integration_id'] = integration_id
            result['iar_file'] = iar_filepath

            print(f"✅ IAR file generated: {iar_filepath}")
            return True, result

        except Exception as e:
            result['errors'].append(f"Processing error: {str(e)}")
            return False, result