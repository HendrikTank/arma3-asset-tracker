import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration with secure defaults."""
    
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost/asset_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pooling for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,  # Verify connections before using them
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
    }
    
    # Session security (critical for production behind Traefik)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', 3600))  # 1 hour default
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Don't expire CSRF tokens
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Application settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')  # 'json' or 'text'
    
    # Environment
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = 'development'
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration with strict security."""
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True  # Force HTTPS
    
    # Validate required environment variables in production
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Ensure critical settings are configured
        assert os.environ.get('SECRET_KEY'), 'SECRET_KEY must be set in production'
        assert os.environ.get('DATABASE_URL'), 'DATABASE_URL must be set in production'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}