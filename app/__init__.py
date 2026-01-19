from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import logging
from logging.handlers import RotatingFileHandler
import json

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Apply ProxyFix middleware for reverse proxy (Traefik)
    # This tells Flask to trust X-Forwarded-* headers from the proxy
    if app.config['ENV'] == 'production':
        app.wsgi_app = ProxyFix(
            app.wsgi_app, 
            x_for=1,      # Trust X-Forwarded-For
            x_proto=1,    # Trust X-Forwarded-Proto (needed for CSRF with HTTPS)
            x_host=1,     # Trust X-Forwarded-Host
            x_port=1      # Trust X-Forwarded-Port
        )
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # Configure Talisman for security headers (only in production behind Traefik)
    if app.config['ENV'] == 'production':
        Talisman(
            app,
            force_https=False,  # Traefik handles TLS termination
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy={
                'default-src': ["'self'"],
                'script-src': ["'self'", "https://cdn.jsdelivr.net"],
                'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
                'font-src': ["'self'", "https://cdn.jsdelivr.net"],
                'img-src': ["'self'", "data:", "https:"],
            },
            content_security_policy_nonce_in=['script-src'],
            frame_options='DENY',
            frame_options_allow_from=None,
        )
    
    # Configure logging
    configure_logging(app)
    
    # Make session available in templates
    @app.context_processor
    def inject_session():
        from flask import session
        return dict(session=session)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if app.config['DEBUG']:
            return str(error), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        if app.config['DEBUG']:
            return str(error), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if app.config['DEBUG']:
            return str(error), 403
        return render_template('errors/403.html'), 403
    
    # Health check endpoints for Traefik
    @app.route('/health')
    def health_check():
        """Basic health check endpoint."""
        return jsonify({'status': 'healthy'}), 200
    
    @app.route('/ready')
    def readiness_check():
        """Readiness check that verifies database connectivity."""
        try:
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'ready', 'database': 'connected'}), 200
        except Exception as e:
            app.logger.error(f'Readiness check failed: {e}')
            return jsonify({'status': 'not ready', 'database': 'disconnected'}), 503
    
    # Register blueprints
    from app.routes import main as main_blueprint
    from app.auth import auth as auth_blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    return app


def configure_logging(app):
    """Configure structured logging for production."""
    if app.config['ENV'] == 'production':
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Configure file handler with rotation
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        # Use JSON formatting for production logs
        if app.config.get('LOG_FORMAT') == 'json':
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
        
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('Application startup')
    else:
        # Simple console logging for development
        app.logger.setLevel(logging.DEBUG)


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)