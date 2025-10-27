import json
import logging
from mcp.server.fastmcp import FastMCP
from connector import SQLServerConnector
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import contextlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key configuration
API_KEY = os.environ.get("X_API_KEY", None)

# Allowed views to expose
ALLOWED_VIEWS = {
    'vw_ActiveSuppliers', 'vw_ProductStockSummary', 'vw_RecentStockMovements'
}

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate X-API-Key header for all API requests."""

    async def dispatch(self, request: Request, call_next):
        # Skip API key check for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        # If API_KEY is not configured, allow all requests (backward compatibility)
        if API_KEY is None:
            logger.warning("X_API_KEY not configured - API key authentication disabled")
            return await call_next(request)

        # Check for X-API-Key header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.warning(f"Missing X-API-Key header from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"error": "Missing X-API-Key header"}
            )

        if api_key != API_KEY:
            logger.warning(f"Invalid X-API-Key from {request.client.host}")
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key"}
            )

        # API key is valid, proceed with request
        return await call_next(request)

mcp = FastMCP("sql-server-mcp")

try:
    connector = SQLServerConnector()
except Exception as e:
    logger.warning(f"Failed to initialize connector: {e}")
    connector = None

def _append_business_area_filter(query: str, user_mail: str) -> str:
    """
    Inject user-specific BusinessArea filter into a SELECT query,
    considering existing WHERE, ORDER BY, GROUP BY clauses.
    """
    filter_sql = (
        "WHERE [Plant] COLLATE SQL_Latin1_General_CP1_CI_AS IN ("
        "SELECT DISTINCT [BusinessArea] "
        "FROM [Salesdashboard-SCL].[dbo].[tbl_User_Mapping] "
        f"WHERE [EMailID] = '{user_mail}')"
    )

    upper_query = query.upper()

    # Identify clauses after WHERE for correct insertion
    import re

    post_where_pattern = re.compile(
        r'\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|OFFSET|FETCH|FOR\s+XML|FOR\s+JSON|OPTION)\b',
        re.IGNORECASE
    )

    if "WHERE" in upper_query:
        # Append filter condition after existing WHERE clause with AND
        where_index = upper_query.index("WHERE") + len("WHERE")
        post_clause_match = post_where_pattern.search(query)

        if post_clause_match:
            # Insert filter before the post clause
            before_post_clause = query[:post_clause_match.start()]
            post_clause = query[post_clause_match.start():]
            modified_query = (
                before_post_clause + f" AND {filter_sql} " + post_clause
            )
        else:
            # Append filter at end of query
            modified_query = query + f" AND {filter_sql}"
    else:
        # No WHERE clause, insert WHERE with filter before any trailing clauses
        post_clause_match = post_where_pattern.search(query)

        if post_clause_match:
            before_post_clause = query[:post_clause_match.start()]
            post_clause = query[post_clause_match.start():]
            modified_query = (
                before_post_clause + f" WHERE {filter_sql} " + post_clause
            )
        else:
            modified_query = query + f" WHERE {filter_sql}"

    logger.info(f"Modified SQL Query for user {user_mail}: {modified_query}")
    return modified_query

@mcp.tool()
def execute_query(query: str, parameters: list[str] = None, user_mail: str = None) -> str:
    """Execute SELECT queries ONLY on allowed views, with embedded BusinessArea user filter."""
    if not connector:
        return "Error: Database connector not initialized"

    if parameters is None:
        parameters = []

    query_upper = query.strip().upper()

    # Only permit SELECT queries
    if not query_upper.startswith("SELECT"):
        return "Only SELECT queries are permitted."

    # Check if the query references any allowed views (simple substring check)
    if not any(view.upper() in query_upper for view in ALLOWED_VIEWS):
        return "Querying this view is not permitted."

    # Append user-specific BusinessArea filter if user_mail provided
    if user_mail:
        query = _append_business_area_filter(query, user_mail)
    else:
        logger.info(f"Executing query without user filter: {query}")

    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in results]
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Query execution failed: {str(e)}"

@mcp.tool()
def get_views() -> str:
    """Return only the permitted views."""
    if not connector:
        return "Error: Database connector not initialized"
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            # Use parameterized query to avoid injection
            placeholders = ','.join('?' for _ in ALLOWED_VIEWS)
            sql = f"""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.VIEWS
                WHERE TABLE_NAME IN ({placeholders})
                ORDER BY TABLE_SCHEMA, TABLE_NAME;
            """
            cursor.execute(sql, tuple(ALLOWED_VIEWS))
            tables = [{"schema": row[0], "view": row[1]} for row in cursor.fetchall()]
            return json.dumps(tables, indent=2)
    except Exception as e:
        return f"Failed to get views: {str(e)}"

@mcp.tool()
def get_view_schema(view_name: str) -> str:
    """Return schema only for permitted views."""
    if view_name not in ALLOWED_VIEWS:
        return "Access denied: View not permitted."
    if not connector:
        return "Error: Database connector not initialized"
    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION;
            """, view_name)
            columns = [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2],
                    "default_value": row[3]
                }
                for row in cursor.fetchall()
            ]
            return json.dumps(columns, indent=2)
    except Exception as e:
        return f"Failed to get schema: {str(e)}"

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)

# Add API Key middleware
app.add_middleware(APIKeyMiddleware)

app.mount("/api", mcp.streamable_http_app())

@app.get("/health")
async def health_check():
    return {"status": "Application is running"}

PORT = int(os.environ.get("PORT", 3000))
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting MCP server on port {PORT}")
    if API_KEY:
        logger.info("X-API-Key authentication enabled")
    else:
        logger.warning("X-API-Key authentication disabled - set X_API_KEY environment variable to enable")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
 