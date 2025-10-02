from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from extensions import db
from models import MenuItem, Order, User
import os
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ========================
# Dashboard Admin
# ========================
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    total_orders = Order.query.count()
    total_sales = db.session.query(db.func.sum(Order.total)).scalar() or 0
    total_users = User.query.count()
    total_menu = MenuItem.query.count()

    return render_template(
        "pages/admin/admin_dashboard.html",
        total_orders=total_orders,
        total_sales=total_sales,
        total_users=total_users,
        total_menu=total_menu
    )

# ========================
# MENU MANAGEMENT
# ========================
@admin_bp.route("/menu")
@login_required
def manage_menu():
    items = MenuItem.query.order_by(MenuItem.id.desc()).all()
    return render_template("pages/admin/menu_admin.html", items=items)

@admin_bp.route("/menu/add", methods=["GET", "POST"])
@login_required
def add_menu():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        is_active = True if request.form.get("is_active") == "on" else False

        image_file = request.files.get("image")
        filename = None
        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1]
            unique_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4) + ext
            filename = secure_filename(unique_name)
            img_path = os.path.join(current_app.root_path, "static/img", filename)
            image_file.save(img_path)

        new_menu = MenuItem(
            name=name,
            description=description,
            price=price,
            image=filename,
            is_active=is_active
        )
        db.session.add(new_menu)
        db.session.commit()
        flash("Menu berhasil ditambahkan", "success")
        return redirect(url_for("admin.manage_menu"))

    return render_template("pages/admin/menu_admin_add.html")

@admin_bp.route("/menu/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_menu(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if request.method == "POST":
        item.name = request.form["name"]
        item.description = request.form["description"]
        item.price = float(request.form["price"])
        item.is_active = True if request.form.get("is_active") == "on" else False

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1]
            unique_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4) + ext
            filename = secure_filename(unique_name)
            img_path = os.path.join(current_app.root_path, "static/img", filename)
            image_file.save(img_path)
            item.image = filename

        db.session.commit()
        flash("Menu berhasil diperbarui", "success")
        return redirect(url_for("admin.manage_menu"))

    return render_template("pages/admin/menu_admin_edit.html", item=item)

@admin_bp.route("/menu/delete/<int:item_id>")
@login_required
def delete_menu(item_id):
    item = MenuItem.query.get_or_404(item_id)

    if item.image:
        img_path = os.path.join(current_app.root_path, "static/img", item.image)
        if os.path.exists(img_path):
            os.remove(img_path)

    db.session.delete(item)
    db.session.commit()
    flash(f"Menu '{item.name}' berhasil dihapus", "info")
    return redirect(url_for("admin.manage_menu"))

# ========================
# ORDER MANAGEMENT
# ========================
@admin_bp.route("/orders")
@login_required
def manage_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template("pages/admin/admin_orders.html", orders=orders)

# ========================
# USER MANAGEMENT
# ========================
@admin_bp.route("/users")
@login_required
def manage_users():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("pages/admin/admin_user.html", users=users)

@admin_bp.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role_value = request.form.get("role")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email sudah terdaftar, gunakan email lain", "danger")
            return redirect(url_for("admin.add_user"))

        new_user = User(
            name=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role_value  # role varchar (admin, cashier, waiter, kitchen)
        )
        db.session.add(new_user)
        db.session.commit()
        flash("User berhasil ditambahkan", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("pages/admin/admin_add_user.html")

@admin_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.name = request.form["username"]
        user.email = request.form["email"]

        password = request.form.get("password")
        if password:
            user.password_hash = generate_password_hash(password)

        role_value = request.form.get("role")
        if role_value:
            user.role = role_value

        db.session.commit()
        flash("User berhasil diperbarui", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("pages/admin/admin_edit_user.html", user=user)

@admin_bp.route("/users/delete/<int:user_id>")
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.name}' berhasil dihapus", "info")
    return redirect(url_for("admin.manage_users"))


# ========================
# RIWAYAT PESANAN
# ========================
@admin_bp.route("/riwayat_pesanan")
@login_required
def riwayat_pesanan():
    orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("pages/admin/admin_riwayat_pesanan.html", orders=orders)
