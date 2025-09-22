import logging
import os
import pyodbc
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

class AzureSQLConnector:
    def __init__(self):
        self.connection_string: Optional[str] = None
        self.setup_connection()

    def setup_connection(self):
        """Setup Azure SQL connection string"""
        server_name = os.getenv("AZURE_SQL_SERVER")
        database = os.getenv("AZURE_SQL_DATABASE")
        username = os.getenv("AZURE_SQL_USERNAME")
        password = os.getenv("AZURE_SQL_PASSWORD")
        
        if not all([server_name, database, username, password]):
            raise ValueError("Missing required environment variables for Azure SQL connection")
        
        logger.info(f"Connecting to server: {server_name}, database: {database}")
        
        available_drivers = pyodbc.drivers()
        logger.info(f"Available ODBC drivers: {available_drivers}")
        
        # Preferred drivers in order of preference
        preferred_drivers = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server"
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
        
        # Updated connection string with TrustServerCertificate
        self.connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_name};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
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
