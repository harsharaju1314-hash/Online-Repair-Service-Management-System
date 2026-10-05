"""Application entry point for local development."""

import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host=host, port=port, debug=debug_mode)
