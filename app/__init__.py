import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_mail import Mail
from flask_migrate import Migrate
from flask_cors import CORS
from app.config import Config

# -------------------------
# 🔌 Global extensions
# -------------------------
db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")
mail = Mail()
migrate = Migrate()

# -------------------------
# 🚀 App Factory
# -------------------------
def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # -------------------------
    # 🔧 Set up logging
    # -------------------------
    if not app.logger.hasHandlers():  # Prevent adding handlers multiple times
        # Setup logger
        logger = logging.getLogger("MTProtoLogger")
        logger.setLevel(logging.DEBUG)

        # Create a file handler to write the logs to a file
        file_handler = logging.FileHandler("app_log.txt")
        file_handler.setLevel(logging.DEBUG)

        # Create a console handler to display logs in the terminal
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Set formatter for both handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        app.logger = logger  # Assign logger to the app instance for later use in routes

    # -------------------------
    # Enable CORS for cross-origin support
    # -------------------------
    CORS(app)

    # -------------------------
    # Init extensions
    # -------------------------
    db.init_app(app)
    socketio.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Import and register blueprints (inside factory to avoid circular imports)
    from app.routes.auth_routes import auth_bp  # Import routes here
    from app.routes.chat_routes import chat_bp  # Import routes here
    from app.routes.general_routes import general_bp  # Import routes here

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(general_bp)

    # -------------------------
    # Set up default route
    # -------------------------
    @app.route("/")
    def index():
        return "<h2>✅ MTProto Chat is Running!</h2><p>Go to <a href='/login'>Login</a> or <a href='/register'>Register</a></p>"

    return app