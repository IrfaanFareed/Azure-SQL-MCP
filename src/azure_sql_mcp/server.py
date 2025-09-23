import asyncio
import json
import logging
from mcp.server.fastmcp import FastMCP
from connector import AzureSQLConnector
import os
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
mcp = FastMCP("azure-sql-mcp")

# Create connector instance
connector = AzureSQLConnector()

import json
import logging
from mcp.server.fastmcp import FastMCP
from connector import AzureSQLConnector
import os
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
mcp = FastMCP("azure-sql-mcp")

# Create connector instance
try:
    connector = AzureSQLConnector()
except Exception as e:
    logger.warning(f"Failed to initialize connector: {e}")
    connector = None

@mcp.tool()
def execute_query(query: str, parameters: list[str] = None) -> str:
    """Execute a SQL query on Azure SQL Database"""
    if not connector:
        return "Error: Database connector not initialized"
    
    if parameters is None:
        parameters = []
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            
            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                # Format results as JSON
                data = []
                for row in results:
                    data.append(dict(zip(columns, row)))
                
                return json.dumps(data, indent=2, default=str)
            else:
                conn.commit()
                return "Query executed successfully"
    except Exception as e:
        return f"Query execution failed: {str(e)}"

@mcp.tool()
def get_tables() -> str:
    """Get list of tables in the database"""
    if not connector:
        return "Error: Database connector not initialized"
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            return json.dumps(tables, indent=2)
    except Exception as e:
        return f"Failed to get tables: {str(e)}"

@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """Get schema information for a specific table"""
    if not connector:
        return "Error: Database connector not initialized"
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, table_name)
            
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2],
                    "default_value": row[3]
                })
            
            return json.dumps(columns, indent=2)
    except Exception as e:
        return f"Failed to get schema: {str(e)}"
 
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
import contextlib
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/", mcp.streamable_http_app())
PORT = os.environ.get("PORT", 8000)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
 
