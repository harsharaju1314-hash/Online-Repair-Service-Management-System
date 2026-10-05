import logging
import os
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request
from app.config import config_by_name
from app.db import close_db, init_db, seed_db, get_db

def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Configure structured application logging
    setup_logging(app)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Register Blueprints
    from app.auth import auth_bp
    from app.routes import routes_bp
    from app.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(api_bp)

    # ----------------- Health Check Endpoint -----------------
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for container and deployment liveness verification."""
        db_status = "disconnected"
        http_code = 200
        try:
            db = get_db()
            db.execute("SELECT 1").fetchone()
            db_status = "connected"
        except Exception as e:
            app.logger.error(f"Health check database ping failed: {e}")
            db_status = f"unhealthy: {str(e)}"
            http_code = 503

        payload = {
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": config_name
        }
        return jsonify(payload), http_code

    # ----------------- Error Handlers -----------------
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Bad Request", "message": str(error)}), 400
        return render_template('base.html', error_title="400 - Bad Request", error_message="The request could not be processed due to invalid syntax."), 400

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Resource Not Found"}), 404
        return render_template('base.html', error_title="404 - Not Found", error_message="The requested page or resource could not be found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal Server Error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500
        return render_template('base.html', error_title="500 - Server Error", error_message="An internal server error occurred. Please try again later."), 500

    # Auto-initialize and seed database for non-testing environments if not exists
    if not app.config['TESTING']:
        with app.app_context():
            try:
                init_db()
                seed_db()
                app.logger.info("Database initialized and default seeds checked.")
            except Exception as e:
                app.logger.warning(f"Database auto-init notice: {e}")

    return app

def setup_logging(app):
    """Configure application logging formatters and handlers."""
    log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    formatter = logging.Formatter(log_format)

    # Console / Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    app.logger.addHandler(stream_handler)

    # File handler if configured
    log_file = app.config.get('LOG_FILE')
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not configure log file {log_file}: {e}")

    app.logger.setLevel(logging.INFO)
