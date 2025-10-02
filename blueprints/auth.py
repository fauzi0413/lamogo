from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Login berhasil", "success")

            # 🔥 Arahkan sesuai role
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user.role == "cashier":
                return redirect(url_for("cashier.dashboard"))
            elif user.role == "waiter":
                return redirect(url_for("waiter.dashboard"))   # ➝ buat nanti
            elif user.role == "kitchen":
                return redirect(url_for("kitchen.dashboard")) # ➝ buat nanti
            else:
                flash("Role tidak dikenali", "danger")
                return redirect(url_for("auth.login"))

        flash("Email atau password salah", "danger")

    return render_template("pages/auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Logout berhasil", "info")
    return redirect(url_for("auth.login"))
