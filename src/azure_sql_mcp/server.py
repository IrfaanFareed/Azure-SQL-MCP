import asyncio
import json
import logging
from mcp.server.fastmcp import FastMCP
from connector import SQLServerConnector
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
mcp = FastMCP("sql-server-mcp")

# Create connector instance
try:
    connector = SQLServerConnector()
except Exception as e:
    logger.warning(f"Failed to initialize connector: {e}")
    connector = None

@mcp.tool()
def execute_query(query: str, parameters: list[str] = None, user_id: str = None) -> str:
    """Execute a SQL query on SQL Server Database to perform only select operations based on the data from the get_views and get_view_schema tools."""
    if not connector:
        return "Error: Database connector not initialized"
    
    if parameters is None:
        parameters = []
    
    # Inject user_id filter for SELECT queries
    if user_id and query.strip().upper().startswith("SELECT"):
        query = _inject_user_id_filter(query, user_id)
        return query
        
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

def _inject_user_id_filter(query: str, user_id: str) -> str:
    """Inject user_id filter into SELECT query while preserving other clauses"""
    import re
    
    # Pattern to find WHERE clause and capture everything after it
    # This handles ORDER BY, GROUP BY, HAVING, LIMIT, OFFSET, etc.
    where_pattern = re.compile(r'\bWHERE\b', re.IGNORECASE)
    
    # Find clauses that should come after WHERE (ORDER BY, GROUP BY, etc.)
    post_where_pattern = re.compile(
        r'\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|OFFSET|FETCH|FOR\s+XML|FOR\s+JSON|OPTION)\b',
        re.IGNORECASE
    )
    
    query_upper = query.upper()
    
    if 'WHERE' in query_upper:
        # Query already has WHERE clause
        # Find the position of WHERE
        where_match = where_pattern.search(query)
        if where_match:
            where_pos = where_match.end()
            
            # Find the first post-WHERE clause (ORDER BY, GROUP BY, etc.)
            post_where_match = post_where_pattern.search(query, where_pos)
            
            if post_where_match:
                # Insert user_id condition before the post-WHERE clause
                before_post_clause = query[:post_where_match.start()]
                post_clause = query[post_where_match.start():]
                modified_query = f"{before_post_clause} AND user_id = '{user_id}' {post_clause}"
            else:
                # No post-WHERE clause, just append at the end
                modified_query = f"{query} AND user_id = '{user_id}'"
    else:
        # Query doesn't have WHERE clause
        # Find the first post-WHERE clause (ORDER BY, GROUP BY, etc.)
        post_where_match = post_where_pattern.search(query)
        
        if post_where_match:
            # Insert WHERE clause before the post-WHERE clause
            before_post_clause = query[:post_where_match.start()]
            post_clause = query[post_where_match.start():]
            modified_query = f"{before_post_clause} WHERE user_id = '{user_id}' {post_clause}"
        else:
            # No post-WHERE clause, just append WHERE at the end
            modified_query = f"{query} WHERE user_id = '{user_id}'"
    
    return modified_query

@mcp.tool()
def get_views() -> str:
    """Get list of views in the database"""
    if not connector:
        return "Error: Database connector not initialized"
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_SCHEMA AS SchemaName,
                TABLE_NAME AS ViewName
                FROM INFORMATION_SCHEMA.VIEWS
                ORDER BY TABLE_SCHEMA, TABLE_NAME;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            return json.dumps(tables, indent=2)
    except Exception as e:
        return f"Failed to get tables: {str(e)}"

@mcp.tool()
def get_view_schema(view_name: str) -> str:
    """Get schema information for a specific view"""
    if not connector:
        return "Error: Database connector not initialized"
    
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COLUMN_NAME  AS ColumnName,
                DATA_TYPE    AS DataType,
                IS_NULLABLE    AS IsNullable,
                COLUMN_DEFAULT As Description
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY TABLE_SCHEMA, ORDINAL_POSITION;
            """, view_name)
            
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
app.mount("/api", mcp.streamable_http_app())

@app.get("/health")
async def health_check():
    return {"status": "Application is running"}

PORT = int(os.environ.get("PORT", 3000))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
 
