from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from extensions import db
from models import MenuItem, Order
from models import User

import os
import secrets
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from werkzeug.security import generate_password_hash

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

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


# Halaman Management Menu (hanya tabel & tombol tambah)
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
        
        image_file = request.files.get("image")
        filename = None
        if image_file and image_file.filename:
            # ambil ekstensi file asli
            ext = os.path.splitext(image_file.filename)[1]
            # generate nama unik
            unique_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4) + ext
            filename = secure_filename(unique_name)
            
            img_path = os.path.join(current_app.root_path, "static/img", filename)
            image_file.save(img_path)

        m = MenuItem(name=name, description=description, price=price, image=filename)
        db.session.add(m)
        db.session.commit()
        flash("Menu berhasil ditambahkan", "success")
        return redirect(url_for("admin.manage_menu"))

    return render_template("pages/admin/menu_admin_add.html")

# Halaman Edit Menu
@admin_bp.route("/menu/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_menu(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if request.method == "POST":
        item.name = request.form["name"]
        item.description = request.form["description"]
        item.price = float(request.form["price"])

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1]
            unique_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4) + ext
            filename = secure_filename(unique_name)
            
            img_path = os.path.join(current_app.root_path, "static/img", filename)
            image_file.save(img_path)
            
            item.image = filename  # update nama gambar

        db.session.commit()
        flash("Menu berhasil diperbarui", "success")
        return redirect(url_for("admin.manage_menu"))

    return render_template("pages/admin/menu_admin_edit.html", item=item)

@admin_bp.route("/orders")
@login_required
def manage_orders():
    orders = Order.query.all()
    return render_template("orders.html", orders=orders)

@admin_bp.route("/delete/<int:item_id>")
@login_required
def delete_menu(item_id):
    item = MenuItem.query.get_or_404(item_id)

    # Hapus file gambar dari folder img
    if item.image:
        img_path = os.path.join(current_app.root_path, "static/img", item.image)
        if os.path.exists(img_path):
            os.remove(img_path)

    # Hapus data menu dari database
    db.session.delete(item)
    db.session.commit()
    flash(f"Menu '{item.name}' berhasil dihapus", "info")
    return redirect(url_for("admin.manage_menu"))


# Halaman Management User (tabel & tombol tambah)
@admin_bp.route("/users")
@login_required
def manage_users():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("pages/admin/admin_user.html", users=users)

# Halaman Tambah User
@admin_bp.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role_value = request.form.get("role")  # string langsung

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email sudah terdaftar, gunakan email lain", "danger")
            return redirect(url_for("admin.add_user"))

        new_user = User(
            name=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role_value
        )
        db.session.add(new_user)
        db.session.commit()
        flash("User berhasil ditambahkan", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("pages/admin/admin_add_user.html")


# Halaman Edit User
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

# Hapus User
@admin_bp.route("/users/delete/<int:user_id>")
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.name}' berhasil dihapus", "info")
    return redirect(url_for("admin.manage_users"))
