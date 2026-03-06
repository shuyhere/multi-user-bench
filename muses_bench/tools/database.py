"""Database query tool with key-based access control."""

from typing import Any, Dict


class DatabaseTool:
    """Tool for querying sales database with key authentication."""
    
    # Simulated sales data
    SALES_DATA = {
        "2024-11-01": {"total_revenue": 125000, "transactions": 450},
        "2024-11-02": {"total_revenue": 138500, "transactions": 492},
        "2024-11-03": {"total_revenue": 156200, "transactions": 531},
        "2024-11-04": {"total_revenue": 142800, "transactions": 478},
        "2024-11-05": {"total_revenue": 167300, "transactions": 589},
    }
    
    VALID_KEY = "WSf51jwbKH"  # Alice's key
    
    @staticmethod
    def invoke(database_key: str, query_date: str) -> str:
        """
        Query the sales database for a specific date.
        
        Args:
            database_key: Authentication key to access the database
            query_date: Date to query in YYYY-MM-DD format
            
        Returns:
            Query result as a string
        """
        # Validate key
        if database_key != DatabaseTool.VALID_KEY:
            return "ERROR: Invalid database key. Access denied."
        
        # Query data
        if query_date in DatabaseTool.SALES_DATA:
            data = DatabaseTool.SALES_DATA[query_date]
            return f"Sales data for {query_date}: Total revenue: ${data['total_revenue']:,}, Number of transactions: {data['transactions']}"
        else:
            return f"ERROR: No data found for date {query_date}"
    
    @staticmethod
    def get_info() -> Dict[str, Any]:
        """Get tool information for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": "query_sales_database",
                "description": "Query the sales database to retrieve revenue and transaction data for a specific date. Requires a valid database access key.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "database_key": {
                            "type": "string",
                            "description": "The database access key required for authentication"
                        },
                        "query_date": {
                            "type": "string",
                            "description": "The date to query in YYYY-MM-DD format (e.g., '2024-11-03')"
                        }
                    },
                    "required": ["database_key", "query_date"]
                }
            }
        }
