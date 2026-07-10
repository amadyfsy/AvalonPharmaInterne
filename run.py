import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app

config_name = os.environ.get("FLASK_CONFIG", "development")
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = app.config.get("DEBUG", False)
    app.run(debug=debug, host="0.0.0.0", port=port)
