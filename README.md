# SQL Server MCP Server

A Model Context Protocol (MCP) server that provides secure, read-only access to specific SQL Server views with automatic user-based filtering. This server enables AI assistants to query predefined database views through a standardized MCP interface with built-in security controls.

## Features

- **View-Only Access**: Read-only SELECT queries on whitelisted database views
- **User-Based Filtering**: Automatic BusinessArea filtering based on user email
- **Secure by Design**: Only SELECT queries allowed, no data modification
- **API Key Authentication**: Optional X-API-Key header authentication for enhanced security
- **View Schema Discovery**: Get detailed schema information for permitted views
- **ODBC Connection**: Supports multiple ODBC drivers with SQL authentication
- **FastMCP Framework**: Built with FastMCP for rapid MCP server development
- **Health Monitoring**: Built-in health check endpoint

## Installation

### Prerequisites

- Python 3.8 or higher
- SQL Server (on-premises or accessible instance)
- ODBC Driver 17 or 18 for SQL Server
- SQL Server authentication credentials (username/password)

### Installing ODBC Driver

Download and install the Microsoft ODBC Driver for SQL Server:
- [ODBC Driver 18 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) (Recommended)
- [ODBC Driver 17 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### From Source

1. Clone the repository:
```bash
git clone https://github.com/IrfaanFareed/Azure-SQL-MCP.git
cd Azure-SQL-MCP
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### From PyPI

```bash
pip install sql-server-mcp
```

## Configuration

Create a `.env` file in the project root with your SQL Server connection details:

```env
# Required
SQL_SERVER=your_server_name
SQL_DATABASE=your_database_name
SQL_USERNAME=your_username
SQL_PASSWORD=your_password

# Optional
SQL_PORT=1433
SQL_ENCRYPT=yes
SQL_TRUST_SERVER_CERT=yes
PORT=3000
X_API_KEY=your-secret-api-key-here
```

### Configuration Parameters

- **SQL_SERVER** (required): Server name or IP address (e.g., `localhost` or `192.168.1.100`)
- **SQL_DATABASE** (required): Database name (e.g., `Salesdashboard-SCL`)
- **SQL_USERNAME** (required): SQL Server authentication username
- **SQL_PASSWORD** (required): SQL Server authentication password
- **SQL_PORT** (optional): Port number (default: 1433)
- **SQL_ENCRYPT** (optional): Enable encryption - `yes`/`true` to enable (default: disabled)
- **SQL_TRUST_SERVER_CERT** (optional): Trust server certificate - `yes`/`true` to trust (default: yes)
- **PORT** (optional): HTTP server port (default: 3000)
- **X_API_KEY** (optional): API key for authentication - if set, all requests must include `X-API-Key` header

### Example Configuration

```env
SQL_SERVER=192.168.1.100
SQL_DATABASE=Salesdashboard-SCL
SQL_USERNAME=mcp_user
SQL_PASSWORD=SecurePassword123!
SQL_PORT=1433
SQL_ENCRYPT=yes
SQL_TRUST_SERVER_CERT=yes
PORT=3000
X_API_KEY=my-super-secret-key-12345
```

### Allowed Views

The server only permits queries on these predefined views:
- `vw_ActiveSuppliers`
- `vw_ProductStockSummary`
- `vw_RecentStockMovements`

To modify the allowed views, edit the `ALLOWED_VIEWS` set in `src/azure_sql_mcp/server.py`:

## Usage

### Starting the Server

#### Development Mode

Run the MCP server directly:

```bash
python src/azure_sql_mcp/server.py
```

#### Service Mode

Use the service runner for production/background operation:

```bash
python src/azure_sql_mcp/service_runner.py
```

The server will start on port 3000 (or the port specified in your `.env` file) and expose:
- MCP endpoint: `http://localhost:3000/api`
- Health check: `http://localhost:3000/health`

### Available MCP Tools

The server exposes the following MCP tools:

#### 1. `execute_query`
Execute SELECT queries on allowed views with automatic user-based filtering.

**Parameters:**
- `query` (string, required): SQL SELECT query to execute (must reference an allowed view)
- `parameters` (list[string], optional): Query parameters for parameterized queries
- `user_mail` (string, optional): User email for automatic BusinessArea filtering

**Returns:** JSON array of query results

**Example:**
```json
{
  "query": "SELECT * FROM vw_ActiveSuppliers WHERE Country = 'USA'",
  "user_mail": "john.doe@example.com"
}
```

**With user_mail**, the query is automatically modified to:
```sql
SELECT * FROM vw_ActiveSuppliers 
WHERE Country = 'USA' 
AND [BusinessArea] IN (
  SELECT DISTINCT [BusinessArea] 
  FROM [Salesdashboard-SCL].[dbo].[tbl_User_Mapping] 
  WHERE [EMailID] = 'john.doe@example.com'
)
```

**Security:**
- Only SELECT queries are permitted
- Query must reference at least one allowed view
- All other query types return an error

#### 2. `get_views`
Get a list of all permitted database views.

**Parameters:** None

**Returns:** JSON array of view schemas and names

**Example Response:**
```json
[
  {
    "schema": "dbo",
    "view": "vw_ActiveSuppliers"
  },
  {
    "schema": "dbo",
    "view": "vw_ProductStockSummary"
  },
  {
    "schema": "dbo",
    "view": "vw_RecentStockMovements"
  }
]
```

#### 3. `get_view_schema`
Get detailed schema information for a specific permitted view.

**Parameters:**
- `view_name` (string, required): Name of the view (must be in allowed list)

**Returns:** JSON array of column definitions

**Example:**
```json
{
  "view_name": "vw_ActiveSuppliers"
}
```

**Example Response:**
```json
[
  {
    "column_name": "SupplierID",
    "data_type": "int",
    "is_nullable": "NO",
    "default_value": null
  },
  {
    "column_name": "SupplierName",
    "data_type": "nvarchar",
    "is_nullable": "YES",
    "default_value": null
  },
  {
    "column_name": "BusinessArea",
    "data_type": "nvarchar",
    "is_nullable": "YES",
    "default_value": null
  }
]
```

**Security:**
- Only permitted views can be queried
- Attempting to access non-allowed views returns "Access denied"

## Security Features

### Read-Only Access

The server enforces strict read-only access:
- **Only SELECT queries permitted**: All other query types (INSERT, UPDATE, DELETE, DROP, etc.) are rejected
- **View-only access**: Only queries referencing allowed views are executed
- **No schema modifications**: Cannot create, alter, or drop database objects

### User-Based BusinessArea Filtering

When a `user_mail` parameter is provided to `execute_query`, the server automatically injects a filter to restrict data based on the user's business areas:

**Original Query:**
```sql
SELECT * FROM vw_ActiveSuppliers WHERE Country = 'USA'
```

**Modified Query (with user_mail):**
```sql
SELECT * FROM vw_ActiveSuppliers 
WHERE Country = 'USA' 
AND [BusinessArea] IN (
  SELECT DISTINCT [BusinessArea] 
  FROM [Salesdashboard-SCL].[dbo].[tbl_User_Mapping] 
  WHERE [EMailID] COLLATE SQL_Latin1_General_CP1_CI_AS = 'user@example.com' COLLATE SQL_Latin1_General_CP1_CI_AS
)
```

The filter is intelligently inserted:
- Handles existing WHERE clauses (appends with AND)
- Respects ORDER BY, GROUP BY, HAVING, and other SQL clauses
- Uses proper collation for email matching

### View Access Control

Only three predefined views are accessible:
```python
ALLOWED_VIEWS = {
    'vw_ActiveSuppliers', 
    'vw_ProductStockSummary', 
    'vw_RecentStockMovements'
}
```

Any query not referencing these views is rejected with: `"Querying this view is not permitted."`

### Connection Security

- **SQL Authentication**: Uses username/password authentication
- **Optional Encryption**: Supports TLS encryption with `SQL_ENCRYPT=yes`
- **Certificate Trust**: Configurable certificate validation
- **Connection Timeout**: 30-second timeout to prevent hanging connections
- **Error Handling**: Detailed error logging without exposing sensitive information

### API Key Authentication

The server supports optional API key authentication via the `X-API-Key` header:

**Enabling API Key Authentication:**
1. Set `X_API_KEY` environment variable in your `.env` file
2. All requests to `/api` endpoint must include `X-API-Key` header
3. Health check endpoint (`/health`) remains accessible without authentication

**Making Authenticated Requests:**

```bash
# With curl
curl -H "X-API-Key: your-api-key-here" http://localhost:3000/api

# With PowerShell
$headers = @{ "X-API-Key" = "your-api-key-here" }
Invoke-WebRequest -Uri http://localhost:3000/api -Headers $headers
```

**Security Responses:**
- `401 Unauthorized`: Missing `X-API-Key` header
- `403 Forbidden`: Invalid API key
- `200 OK`: Valid API key, request processed

**Note:** If `X_API_KEY` is not set in environment variables, API key authentication is disabled for backward compatibility.

## Architecture

```
src/
  azure_sql_mcp/
    ├── __init__.py          # Package initialization
    ├── connector.py         # SQL Server connection management (pyodbc)
    ├── server.py            # MCP server implementation (FastMCP + FastAPI)
    └── service_runner.py    # Service launcher with logging
```

### Key Components

**SQLServerConnector** (`connector.py`):
- Manages ODBC connections to SQL Server
- Supports ODBC Driver 17, 18, or legacy SQL Server driver
- Handles authentication with username/password
- Configurable encryption and certificate trust
- Connection pooling via context manager

**MCP Server** (`server.py`):
- Built with **FastMCP** framework
- Exposes 3 MCP tools: `execute_query`, `get_views`, `get_view_schema`
- Implements automatic BusinessArea filtering
- View whitelist enforcement
- FastAPI integration for HTTP endpoints

**Service Runner** (`service_runner.py`):
- Production-ready service launcher
- Configurable logging to file and console
- Runs on configurable port (default: 3000)
- Uses Uvicorn ASGI server

### Dependencies

- **mcp** (>=1.0.0): Model Context Protocol framework
- **pyodbc** (>=4.0.0): SQL Server ODBC driver interface
- **python-dotenv** (>=1.0.0): Environment variable management
- **uvicorn**: ASGI server
- **fastapi**: Web framework for HTTP endpoints

## Development

### Project Setup

1. Clone and install:
```bash
git clone https://github.com/IrfaanFareed/Azure-SQL-MCP.git
cd Azure-SQL-MCP
pip install -r requirements.txt
```

2. Create `.env` file with your configuration

3. Run the server:
```bash
python src/azure_sql_mcp/server.py
```

### Running Tests

```bash
pytest tests/
```

### Code Style

This project follows Python best practices:
- **Black** for code formatting (line length: 88)
- **Flake8** for linting
- **MyPy** for type checking

Format code:
```bash
black src/
```

Run linters:
```bash
flake8 src/
mypy src/
```

### Adding New Views

To allow access to additional views, edit `server.py`:

```python
# Add view names to the allowed set
ALLOWED_VIEWS = {
    'vw_ActiveSuppliers', 
    'vw_ProductStockSummary', 
    'vw_RecentStockMovements',
    'vw_YourNewView'  # Add your view here
}
```

### Logging

The server logs to:
- **Console**: Real-time logging output
- **File**: `C:\Projects\SQL-MCP\service.log` (when using service_runner.py)

Configure logging level in the respective Python files.

### Building the Package

```bash
python -m build
```

This creates distribution files in `dist/`:
- `.tar.gz` (source distribution)
- `.whl` (wheel distribution)

## Use Cases

### Sales Dashboard Integration

This server was designed for secure AI assistant access to sales dashboards:
- Sales representatives query their specific business area data
- Managers view aggregated metrics across teams
- Automatic filtering prevents cross-contamination of business area data

### Example Workflow

1. AI assistant receives user query: "Show me active suppliers in the USA"

2. AI calls `execute_query` with user's email:
```json
{
  "query": "SELECT SupplierName, City, State FROM vw_ActiveSuppliers WHERE Country = 'USA'",
  "user_mail": "sales.rep@company.com"
}
```

3. Server automatically filters to user's business areas and returns results

4. AI can then call `get_view_schema` to understand data structure for follow-up queries

### Integration with AI Platforms

#### Claude Desktop

Add to Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sql-server": {
      "command": "python",
      "args": ["C:/Projects/SQL-MCP/src/azure_sql_mcp/server.py"],
      "env": {
        "SQL_SERVER": "your-server",
        "SQL_DATABASE": "your-database",
        "SQL_USERNAME": "your-username",
        "SQL_PASSWORD": "your-password",
        "X_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### Microsoft Copilot Studio

The MCP server can be integrated with Microsoft Copilot Studio through custom HTTP actions. This enables your copilots to query SQL Server data directly.

**Quick Start:**
1. Expose your MCP server (via Azure App Service, Azure Relay, or public endpoint)
2. Create custom actions in Copilot Studio for each MCP tool
3. Configure X-API-Key authentication in action headers (see guide below)
4. Build topics that call these actions with natural language

**📖 Detailed Guides:**
- [How to Pass Custom Headers in Copilot Studio](docs/COPILOT_STUDIO_HEADERS.md) - **Start here for X-API-Key setup**
- [Complete Copilot Studio Integration](docs/COPILOT_STUDIO_INTEGRATION.md) - Full integration guide

**Key Benefits:**
- Natural language queries to SQL Server
- Automatic user-based data filtering
- Secure access with API key authentication
- Integration with Microsoft 365 and Teams
- No coding required in Copilot Studio

**Example Action Configuration:**
```
URL: https://your-server.azurewebsites.net/api
Method: POST
Headers:
  X-API-Key: your-secret-key
  Content-Type: application/json
Body: {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}
```

## API Reference

### HTTP Endpoints

**MCP Endpoint**: `http://localhost:3000/api`
- Handles MCP protocol messages
- Supports streaming responses
- **Requires `X-API-Key` header** if `X_API_KEY` environment variable is set

**Health Check**: `http://localhost:3000/health`
- Returns: `{"status": "Application is running"}`
- Use for monitoring and health checks
- **No authentication required** (always accessible)

**Example Request with API Key:**
```bash
curl -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json" \
     -d '{"method":"tools/list"}' \
     http://localhost:3000/api
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SQL_SERVER | Yes | - | SQL Server hostname or IP |
| SQL_DATABASE | Yes | - | Database name |
| SQL_USERNAME | Yes | - | SQL authentication username |
| SQL_PASSWORD | Yes | - | SQL authentication password |
| SQL_PORT | No | 1433 | SQL Server port |
| SQL_ENCRYPT | No | no | Enable TLS encryption (yes/no) |
| SQL_TRUST_SERVER_CERT | No | yes | Trust server certificate (yes/no) |
| PORT | No | 3000 | HTTP server port |
| X_API_KEY | No | - | API key for authentication (if not set, auth disabled) |

### Connection Issues

**Error: "Database connector not initialized"**
- Verify all required environment variables are set in `.env`
- Check that `SQL_SERVER`, `SQL_DATABASE`, `SQL_USERNAME`, and `SQL_PASSWORD` are provided
- Restart the server after updating `.env`

**Error: "Database connection failed"**
- Verify SQL Server is running and accessible
- Check server name/IP and port are correct
- Test network connectivity: `Test-NetConnection -ComputerName <server> -Port 1433` (PowerShell)
- Verify SQL Server is configured to allow SQL authentication
- Check firewall rules allow connections to SQL Server port

### ODBC Driver Issues

**Error: "No suitable ODBC driver found"**
- Install Microsoft ODBC Driver 17 or 18:
  ```powershell
  winget install Microsoft.ODBCDriver.18
  ```
- Verify installation:
  ```python
  import pyodbc
  print(pyodbc.drivers())
  ```

### Query Execution Errors

**Error: "Only SELECT queries are permitted"**
- The server only allows SELECT queries for security
- Attempting INSERT, UPDATE, DELETE, or DDL statements will fail
- This is intentional to maintain read-only access

**Error: "Querying this view is not permitted"**
- Your query must reference one of the allowed views:
  - `vw_ActiveSuppliers`
  - `vw_ProductStockSummary`
  - `vw_RecentStockMovements`
- To add views, modify `ALLOWED_VIEWS` in `server.py`

**Error: "Access denied: View not permitted" (from get_view_schema)**
- You can only get schemas for allowed views
- Check the view name matches exactly (case-sensitive)

### Authentication Issues

**Error: "Login failed for user"**
- Verify SQL_USERNAME and SQL_PASSWORD are correct
- Ensure SQL Server authentication is enabled (not just Windows auth)
- Check user has appropriate permissions on the database

**Error: "Missing X-API-Key header" (401)**
- Add `X-API-Key` header to your request
- Example: `curl -H "X-API-Key: your-key" http://localhost:3000/api`
- If you don't want API key authentication, remove `X_API_KEY` from `.env`

**Error: "Invalid API key" (403)**
- The provided API key doesn't match the configured `X_API_KEY`
- Verify the API key value in your `.env` file
- Ensure the key is passed correctly in the `X-API-Key` header

### SSL/TLS Issues

**Error: "SSL Provider: The certificate chain was issued by an authority that is not trusted"**
- Set `SQL_TRUST_SERVER_CERT=yes` in `.env`
- Or install the server's SSL certificate in your trusted store

### Health Check

Test if the server is running:
```powershell
Invoke-WebRequest -Uri http://localhost:3000/health
```

Expected response:
```json
{"status": "Application is running"}
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add/update tests as needed
5. Ensure code follows style guidelines (run `black` and `flake8`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Maintain read-only access security model
- Add new views to `ALLOWED_VIEWS` with clear justification
- Include docstrings for all functions
- Write tests for new features
- Update README for any user-facing changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/IrfaanFareed/Azure-SQL-MCP/issues)
- **Repository**: [GitHub Repository](https://github.com/IrfaanFareed/Azure-SQL-MCP)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) by Jeff Lowin
- Uses the [Model Context Protocol](https://modelcontextprotocol.io/) specification
- Powered by [pyodbc](https://github.com/mkleehammer/pyodbc) for SQL Server connectivity
- Web framework by [FastAPI](https://fastapi.tiangolo.com/)
- ASGI server by [Uvicorn](https://www.uvicorn.org/)

## Changelog

### Version 1.0.1 (Current)
- **NEW**: X-API-Key authentication support via `X_API_KEY` environment variable
- Optional API key authentication for enhanced security
- Backward compatible (auth disabled if `X_API_KEY` not set)
- Health endpoint remains publicly accessible
- Detailed logging for authentication events

### Version 1.0.0
- Initial release
- Read-only SQL Server view access via MCP
- Three MCP tools: `execute_query`, `get_views`, `get_view_schema`
- Automatic user-based BusinessArea filtering
- View whitelist security model
- SQL authentication support
- ODBC Driver 17/18 compatibility
- FastAPI HTTP endpoints
- Health monitoring
- Comprehensive error handling and logging

## Roadmap

Potential future enhancements:
- [ ] Support for additional authentication methods (Windows Auth, Azure AD)
- [ ] Query result pagination for large datasets
- [ ] Query performance metrics and caching
- [ ] Configurable view whitelist via environment variables
- [ ] Support for stored procedure execution (read-only)
- [ ] Rate limiting and query timeout controls
- [ ] Audit logging for all queries

