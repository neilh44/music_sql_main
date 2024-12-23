import sqlite3
import logging
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class TableInfo:
    """Store table information including schema and relationships"""
    name: str
    columns: List[Dict[str, Any]]
    relationships: List[Dict[str, str]]

class LLMService:
    def __init__(self, api_key: str, db_path: str):
        """
        Initialize LLM Service
        
        Args:
            api_key: API key for Groq
            db_path: Path to SQLite database
        """
        self.api_key = api_key
        self.db_path = db_path
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.table_info = self._load_database_schema()

    def _load_database_schema(self) -> Dict[str, TableInfo]:
        """Load complete database schema with relationships"""
        schema_info = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    # Get columns
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = [{
                        'name': col[1],
                        'type': col[2],
                        'nullable': not col[3],
                        'primary_key': bool(col[5])
                    } for col in cursor.fetchall()]
                    
                    # Get foreign keys
                    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                    relationships = [{
                        'from_table': table_name,
                        'to_table': fk[2],
                        'from_column': fk[3],
                        'to_column': fk[4]
                    } for fk in cursor.fetchall()]
                    
                    schema_info[table_name] = TableInfo(
                        name=table_name,
                        columns=columns,
                        relationships=relationships
                    )
                    
            return schema_info
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error while loading schema: {e}")
            return {}

    def _prepare_schema_prompt(self) -> str:
        """Prepare a comprehensive schema description for the LLM"""
        prompt = "Database Schema:\n\n"
        
        # Add table schemas
        for table_name, info in self.table_info.items():
            prompt += f"Table: {table_name}\n"
            prompt += "Columns:\n"
            for col in info.columns:
                prompt += f"- {col['name']} ({col['type']})"
                if col['primary_key']:
                    prompt += " PRIMARY KEY"
                if not col['nullable']:
                    prompt += " NOT NULL"
                prompt += "\n"
            
            # Add relationships
            if info.relationships:
                prompt += "Relationships:\n"
                for rel in info.relationships:
                    prompt += f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}\n"
            prompt += "\n"
            
        return prompt

    def _extract_sql_query(self, content: str) -> Optional[str]:
        """
        Extract SQL query from LLM response
        
        Args:
            content: Raw response content from LLM
            
        Returns:
            Extracted SQL query or None if not found
        """
        # Remove markdown code blocks if present
        content = content.replace("```sql", "").replace("```", "").strip()
        
        # Basic validation
        if content.upper().startswith("SELECT"):
            return content
        
        return None

    def _process_context(self, context: Optional[List[Dict]]) -> str:
        """
        Process conversation context into prompt format
        
        Args:
            context: List of previous interactions
            
        Returns:
            Formatted context string for prompt
        """
        if not context:
            return ""
            
        recent_queries = []
        for interaction in context[-3:]:  # Use last 3 interactions
            if isinstance(interaction, dict):
                query = interaction.get('query', '')
                sql = interaction.get('sql_query', '')
                if query and sql:
                    recent_queries.append(f"Previous Query: {query}\nSQL: {sql}")
        
        if recent_queries:
            return "\nRecent queries for context:\n" + "\n\n".join(recent_queries) + "\n"
        
        return ""

    def convert_to_sql_query(
        self, 
        natural_query: str, 
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Convert natural language to SQL query using Groq API
        
        Args:
            natural_query: Natural language query to convert
            context: Optional list of previous interactions
            
        Returns:
            Dictionary containing success status and SQL query or error
        """
        try:
            schema_prompt = self._prepare_schema_prompt()
            context_prompt = self._process_context(context)
            
            system_prompt = f"""
            You are an expert SQL query generator. Your task is to convert natural language queries into valid SQL queries based on the provided database schema.
            
            {schema_prompt}
            
            Rules for generating SQL queries:
            1. Use proper JOIN syntax when relating multiple tables
            2. Consider table relationships and use appropriate JOIN conditions
            3. Handle NULL values appropriately
            4. Use table aliases when necessary for clarity
            5. Return only the requested columns, use * only when specifically asked
            6. Include WHERE clauses based on the natural language conditions
            7. Use appropriate aggregation functions when needed (COUNT, SUM, AVG, etc.)
            8. For time-based queries, use datetime() instead of DATE_SUB:
                Ensure that for time-based conditions, use datetime() (a function supported by SQLite) rather than DATE_SUB or other date manipulation functions like CURRENT_DATE.
                Example Rule:
                "For queries involving date or time ranges (e.g., 'last 2 days', 'since last week', etc.), always use the datetime() function."
                "Example query: SELECT * FROM orders WHERE created_at >= datetime('now', '-2 days');"
            
            {context_prompt}
            
            Generate a SQL query for the following natural language request:
            {natural_query}
            
            Return only the SQL query without any explanation.
            """

            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_query}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }

            self.logger.info(f"Sending request to Groq API for query: {natural_query}")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            self.logger.info(f"Received response from Groq API")
            
            if 'choices' in result and result['choices']:
                sql_query = self._extract_sql_query(result['choices'][0]['message']['content'])
                if sql_query:
                    return {"success": True, "query": sql_query}
            
            return {"success": False, "error": "Failed to generate SQL query"}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request error: {str(e)}")
            return {"success": False, "error": f"API request failed: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Unexpected error in convert_to_sql_query: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query on the database
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Dictionary containing results and column names or error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(sql_query)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            return {
                "success": True,
                "results": results,
                "columns": columns
            }
        except Exception as e:
            self.logger.error(f"Query execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }