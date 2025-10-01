from flask import Flask, redirect, url_for
from config import Config
from extensions import db, migrate, login_manager
from models import User
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.cashier import cashier_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # ⬇️ Tambahkan ini
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan login terlebih dahulu"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # route utama
    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    # register blueprint
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(cashier_bp, url_prefix="/cashier")

    return app
