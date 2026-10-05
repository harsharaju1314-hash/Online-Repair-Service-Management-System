import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-change-me")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "app.db"))
    TESTING = False
    LOG_FILE = os.environ.get("LOG_FILE", os.path.join(BASE_DIR, "app.log"))

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ":memory:"
    SECRET_KEY = "test-secret-key"
    LOG_FILE = None

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
