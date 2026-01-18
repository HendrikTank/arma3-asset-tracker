from app import create_app

app = create_app()

if __name__ == "__main__":
    # Bind to 0.0.0.0 to make it accessible outside the container
    app.run(host='0.0.0.0', port=5000, debug=True)