import logging
import os
import pyodbc
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

class SQLServerConnector:
    def __init__(self):
        self.connection_string: Optional[str] = None
        self.setup_connection()

    def setup_connection(self):
        """Setup SQL Server connection string"""
        server_name = os.environ.get("SQL_SERVER")
        database = os.environ.get("SQL_DATABASE")
        username = os.environ.get("SQL_USERNAME")
        password = os.environ.get("SQL_PASSWORD")
        # Optional settings
        port = os.environ.get("SQL_PORT")
        encrypt = os.environ.get("SQL_ENCRYPT")
        trust_server_cert = os.environ.get("SQL_TRUST_SERVER_CERT")
        
        if not all([server_name, database, username, password]):
            raise ValueError("Missing required environment variables for SQL Server connection")

        logger.info(f"Connecting to server: {server_name}, database: {database}")

        available_drivers = pyodbc.drivers()
        logger.info(f"Available ODBC drivers: {available_drivers}")
        
        # Preferred drivers in order of preference
        preferred_drivers = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server"
        ]
        
        driver = None
        for pref_driver in preferred_drivers:
            if pref_driver in available_drivers:
                driver = pref_driver
                break
        
        if not driver:
            raise ValueError(
                f"No suitable ODBC driver found for SQL Server. "
                f"Available drivers: {available_drivers}. "
                f"Please install Microsoft ODBC Driver 17 or 18 for SQL Server."
            )
        
        # Allow optional port specification. If SQL_PORT provided and the server string
        # does not already include a port (comma) or named instance (backslash), append it.
        server_value = server_name
        if port and ("," not in server_name) and ("\\" not in server_name):
            server_value = f"{server_name},{port}"

        # Encryption and trust settings (defaults tuned for common on-prem setups)
        # SQL_ENCRYPT: 'yes'/'true' to enable Encrypt=yes, otherwise omitted/disabled
        # SQL_TRUST_SERVER_CERT: 'no'/'false' to set TrustServerCertificate=no, otherwise 'yes'
        encrypt_flag = ""
        trust_flag = ""
        if encrypt and encrypt.lower() in ("1", "true", "yes"):
            encrypt_flag = "Encrypt=yes;"
            # default TrustServerCertificate to no if encrypt is enabled unless explicitly set
            if trust_server_cert and trust_server_cert.lower() in ("0", "false", "no"):
                trust_flag = "TrustServerCertificate=no;"
            else:
                trust_flag = "TrustServerCertificate=yes;"
        else:
            # when encryption not requested, set trust flag according to env or default to yes
            if trust_server_cert and trust_server_cert.lower() in ("0", "false", "no"):
                trust_flag = "TrustServerCertificate=no;"
            else:
                trust_flag = "TrustServerCertificate=yes;"

        # Updated connection string for on-premises SQL Server
        self.connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_value};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"{encrypt_flag}"
            f"{trust_flag}"
            f"Connection Timeout=30;"
        )

    def get_connection(self):
        """Get database connection"""
        if not self.connection_string:
            raise ValueError("Connection string not configured")
        
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
