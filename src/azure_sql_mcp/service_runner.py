import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Configure logging for service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'C:\Projects\SQL-MCP\service.log'),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    from server import app
    import uvicorn
    
    # Use port 8080 to avoid IIS conflict
    PORT = int(os.environ.get("PORT", 3000))
    
    print(f"Starting MCP server on port {PORT}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=PORT,
        log_level="info",
        access_log=True
    )
