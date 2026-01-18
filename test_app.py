import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()
print("App created successfully!")
print(f"App name: {app.name}")
print(f"Has auth blueprint: {'auth' in app.blueprints}")
print(f"Has main blueprint: {'main' in app.blueprints}")