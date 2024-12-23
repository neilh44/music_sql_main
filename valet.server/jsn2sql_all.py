import streamlit as st
import json
import sqlite3
from pathlib import Path
import pandas as pd
from typing import List, Dict, Set, Tuple
import logging
from datetime import datetime, timezone
import re
import ijson

class MultiTableJSONConverter:
    def __init__(self, db_path: str = "converted_data.db", batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.table_columns: Dict[str, Set[str]] = {}
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def sanitize_column_name(self, name: str) -> str:
        """Sanitize column names for SQL compatibility"""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it starts with a letter
        if not re.match(r'^[a-zA-Z]', sanitized):
            sanitized = 'col_' + sanitized
        
        # Truncate to reasonable length
        return sanitized[:64].lower()

    def get_table_name_from_file(self, filename: str) -> str:
        """Extract sanitized table name from filename"""
        base_name = Path(filename).stem
        return self.sanitize_column_name(base_name)

    def create_table_schema(self, table_name: str, data: List[Dict]) -> str:
        """Create SQL schema for a table"""
        if not data:
            raise ValueError(f"No data provided for table {table_name}")
        
        # Flatten first item to get all potential columns
        first_item = self.flatten_json(data[0])
        
        # Always include an ID column
        field_definitions = [
            "id TEXT PRIMARY KEY"
        ]
        
        # Add other columns with inferred types
        for field, sample_value in first_item.items():
            if field == 'id':
                continue
            
            # Sanitize field name
            safe_field = self.sanitize_column_name(field)
            
            # Infer and add column
            sql_type = self.infer_sql_type(sample_value)
            field_definitions.append(f"{safe_field} {sql_type}")
        
        # Create table SQL
        create_table_sql = [
            f"CREATE TABLE IF NOT EXISTS {table_name} (",
            "    " + ",\n    ".join(field_definitions),
            ");"
        ]
        return "\n".join(create_table_sql)

    def infer_sql_type(self, value) -> str:
        """Infer SQL data type from Python value"""
        if value is None:
            return "TEXT"
        elif isinstance(value, bool):
            return "INTEGER"  # SQLite uses INTEGER for boolean
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "REAL"
        elif isinstance(value, dict):
            return "TEXT"
        elif isinstance(value, list):
            return "TEXT"
        elif isinstance(value, datetime):
            return "TIMESTAMP"
        else:
            return "TEXT"

    def convert_firebase_timestamp(self, timestamp_dict: Dict) -> str:
        """
        Convert Firebase timestamp to ISO format string
        
        Args:
            timestamp_dict (Dict): Dictionary with _seconds and _nanoseconds
        
        Returns:
            str: ISO format timestamp string
        """
        try:
            seconds = timestamp_dict.get('_seconds', 0)
            nanoseconds = timestamp_dict.get('_nanoseconds', 0)
            
            # Convert to datetime
            dt = datetime.fromtimestamp(seconds + nanoseconds / 1e9, tz=timezone.utc)
            
            # Return ISO format string
            return dt.isoformat()
        except Exception as e:
            self.logger.warning(f"Error converting timestamp: {e}")
            return None

    def flatten_json(self, json_data: Dict) -> Dict:
        """Flatten nested JSON structure with sanitized keys"""
        flat_data = {}
        
        def flatten(data, prefix=''):
            if isinstance(data, dict):
                for key, value in data.items():
                    # Sanitize key
                    safe_key = self.sanitize_column_name(
                        f"{prefix}_{key}" if prefix else key
                    )
                    
                    # Special handling for Firebase timestamps
                    if isinstance(value, dict) and '_seconds' in value and '_nanoseconds' in value:
                        flat_data[safe_key] = self.convert_firebase_timestamp(value)
                    
                    # Handle nested structures
                    elif isinstance(value, dict):
                        flatten(value, prefix=safe_key)
                    
                    elif isinstance(value, list):
                        # Convert list to JSON string, but handle special cases
                        if all(isinstance(item, dict) and '_seconds' in item and '_nanoseconds' in item for item in value):
                            flat_data[safe_key] = json.dumps([
                                self.convert_firebase_timestamp(item) for item in value
                            ])
                        else:
                            flat_data[safe_key] = json.dumps(value)
                    
                    else:
                        flat_data[safe_key] = value
            
            elif isinstance(data, list):
                # Convert list to JSON string
                flat_data[prefix] = json.dumps(data)
            else:
                flat_data[prefix] = data
        
        flatten(json_data)
        return flat_data

    def stream_json(self, file_obj) -> List[Dict]:
        """Stream JSON file efficiently"""
        try:
            # Reset file pointer
            file_obj.seek(0)
            
            # Read entire file content first to validate JSON
            content = file_obj.read()
            file_obj.seek(0)
            
            try:
                # First, validate the entire JSON structure
                parsed_content = json.loads(content)
                
                # If not a list, wrap in a list
                if not isinstance(parsed_content, list):
                    parsed_content = [parsed_content]
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON structure: {e}")
                return []

            return parsed_content
        
        except Exception as e:
            self.logger.error(f"Unexpected error in stream_json: {e}")
            return []

    def convert_json_file(self, uploaded_file):
        """Convert JSON file to SQLite table"""
        # Get sanitized table name
        table_name = self.get_table_name_from_file(uploaded_file.name)
        
        # Stream and process JSON data
        data = self.stream_json(uploaded_file)
        
        if not data:
            st.error(f"No valid data found in {uploaded_file.name}")
            return 0
        
        # Create table schema
        try:
            schema_sql = self.create_table_schema(table_name, data)
            st.code(schema_sql, language="sql")
        
            # Create table and insert data
            with sqlite3.connect(self.db_path) as conn:
                # Create table
                conn.executescript(schema_sql)
                
                # Flatten and insert data
                flattened_data = [self.flatten_json(item) for item in data]
                df = pd.DataFrame(flattened_data)
                
                if not df.empty:
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
        
            return len(data)
        
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            return 0

def main():
    st.title("Multi-Table JSON to SQLite Converter")
    
    uploaded_files = st.file_uploader(
        "Upload JSON files", 
        accept_multiple_files=True,
        type=['json']
    )
    
    if uploaded_files:
        converter = MultiTableJSONConverter()
        
        for uploaded_file in uploaded_files:
            try:
                records_processed = converter.convert_json_file(uploaded_file)
                st.success(f"Processed {records_processed} records from {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    if st.button("Download Database"):
        try:
            with open("converted_data.db", "rb") as f:
                st.download_button(
                    label="Download SQLite Database",
                    data=f,
                    file_name="converted_data.db",
                    mime="application/x-sqlite3"
                )
        except FileNotFoundError:
            st.error("Please create and populate the database first.")

if __name__ == "__main__":
    main()