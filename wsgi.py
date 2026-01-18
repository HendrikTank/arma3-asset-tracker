from app import create_app
import os

# Create app with environment-specific configuration
config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)

if __name__ == "__main__":
    # Only used for development - production uses Waitress/Gunicorn
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)