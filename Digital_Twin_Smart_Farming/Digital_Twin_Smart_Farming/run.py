from app.app import app

if __name__ == "__main__":
    import os
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
