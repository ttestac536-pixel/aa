import os
import csv
from typing import Tuple, List, Dict

class CSVValidator:
    """Validates CSV files before processing"""

    @staticmethod
    def validate_file_exists(filepath: str) -> Tuple[bool, str]:
        """Check if file exists"""
        if not os.path.exists(filepath):
            return False, "File does not exist"
        return True, "File exists"

    @staticmethod
    def validate_file_size(filepath: str, max_size_mb: int = 16) -> Tuple[bool, str]:
        """Check file size"""
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"File size {file_size_mb:.2f}MB exceeds limit {max_size_mb}MB"
        return True, f"File size valid: {file_size_mb:.2f}MB"

    @staticmethod
    def validate_csv_format(filepath: str) -> Tuple[bool, str]:
        """Validate CSV format"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                if not headers:
                    return False, "CSV file has no headers"
                
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    return False, "CSV file has no data rows"
                
                return True, f"CSV format valid: {len(headers)} columns, {row_count} rows"
        except Exception as e:
            return False, f"CSV format error: {str(e)}"

    @staticmethod
    def validate_required_columns(filepath: str, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """Check for required columns"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                missing = [col for col in required_columns if col not in headers]
                
                if missing:
                    return False, missing
                
                return True, []
        except Exception as e:
            return False, [str(e)]

    @staticmethod
    def validate_data_integrity(filepath: str) -> Tuple[bool, List[str]]:
        """Validate data integrity"""
        errors = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for idx, row in enumerate(reader, 1):
                    # Check for empty rows
                    if not any(row.values()):
                        errors.append(f"Row {idx}: Empty row found")
                    
                    # Check for required fields
                    if not row.get('journal_name', '').strip():
                        errors.append(f"Row {idx}: journal_name is required")
                    
                    if not row.get('period', '').strip():
                        errors.append(f"Row {idx}: period is required")
                    
                    if not row.get('account_code', '').strip():
                        errors.append(f"Row {idx}: account_code is required")
                
                if errors:
                    return False, errors
                return True, []
        except Exception as e:
            return False, [str(e)]


class IntegrationValidator:
    """Validates integration configurations"""

    @staticmethod
    def validate_mappings(mappings: Dict) -> Tuple[bool, List[str]]:
        """Validate field mappings"""
        errors = []
        
        if not mappings:
            errors.append("Mappings are empty")
            return False, errors
        
        required_oracle_fields = [
            'JE_BATCH_ID', 'PERIOD_NAME', 'CODE_COMBINATION_ID',
            'ENTERED_DR_AMOUNT', 'ENTERED_CR_AMOUNT', 'DESCRIPTION'
        ]
        
        mapped_values = list(mappings.values())
        for field in required_oracle_fields:
            if field not in mapped_values:
                errors.append(f"Required Oracle field not mapped: {field}")
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_transformations(transformations: Dict) -> Tuple[bool, List[str]]:
        """Validate transformation rules"""
        errors = []
        
        if not transformations:
            errors.append("Transformations are empty")
            return False, errors
        
        required_keys = ['date_format', 'amount_format', 'validation_rules']
        for key in required_keys:
            if key not in transformations:
                errors.append(f"Missing transformation rule: {key}")
        
        return len(errors) == 0, errors


class ConnectionValidator:
    """Validates OIC connections"""

    @staticmethod
    def validate_oic_credentials() -> Tuple[bool, str]:
        """Validate OIC connection credentials"""
        required_env = ['OIC_INSTANCE_URL', 'OIC_USERNAME', 'OIC_PASSWORD']
        
        missing = [var for var in required_env if not os.getenv(var)]
        
        if missing:
            return False, f"Missing environment variables: {', '.join(missing)}"
        
        return True, "OIC credentials available"

    @staticmethod
    def validate_connection_types(connections: Dict) -> Tuple[bool, List[str]]:
        """Validate required connection types"""
        errors = []
        required_connections = ['sap', 'sftp', 'oracle']
        
        for conn in required_connections:
            if conn not in connections:
                errors.append(f"Missing connection: {conn}")
        
        return len(errors) == 0, errors