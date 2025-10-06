from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from extensions import db
from models import MenuItem, Order, User, OrderItem, Feedback
import os
import secrets
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from sqlalchemy import func, extract
from calendar import month_abbr  
from dateutil.relativedelta import relativedelta

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ========================
# Dashboard Admin
# ========================
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    """Tampilan utama dashboard admin berisi ringkasan statistik dan grafik penjualan."""

    # === Statistik Utama ===
    total_orders = Order.query.count()
    total_sales = db.session.query(func.sum(Order.total)).scalar() or 0
    total_users = User.query.count()
    total_menu = MenuItem.query.count()
    avg_order_value = db.session.query(func.avg(Order.total)).scalar() or 0

    # === Statistik Tahunan ===
    yearly_data = (
        db.session.query(
            extract("year", Order.created_at).label("year"),
            func.sum(Order.total).label("total_sales"),
            func.count(Order.id).label("total_orders")
        )
        .group_by("year")
        .order_by("year")
        .all()
    )
    years = [int(y) for y, _, _ in yearly_data]
    yearly_sales = [int(t or 0) for _, t, _ in yearly_data]
    yearly_orders = [int(o or 0) for _, _, o in yearly_data]

    # === Statistik Bulanan (tahun berjalan) ===
    current_year = datetime.now().year
    monthly_data = (
        db.session.query(
            extract("month", Order.created_at).label("month"),
            func.sum(Order.total).label("total_sales"),
            func.count(Order.id).label("total_orders")
        )
        .filter(extract("year", Order.created_at) == current_year)
        .group_by("month")
        .order_by("month")
        .all()
    )

    months = [month_abbr[m] for m in range(1, 13)]
    monthly_sales = [0] * 12
    monthly_orders = [0] * 12
    for m, sales, orders in monthly_data:
        monthly_sales[int(m) - 1] = int(sales or 0)
        monthly_orders[int(m) - 1] = int(orders or 0)

    # === Statistik Mingguan (7 hari terakhir) ===
    today = datetime.now()
    week_start = today - timedelta(days=6)
    weekly_data = (
        db.session.query(
            func.date(Order.created_at).label("date"),
            func.sum(Order.total).label("total_sales"),
            func.count(Order.id).label("total_orders")
        )
        .filter(Order.created_at >= week_start)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    week_days, week_sales, week_orders = [], [], []
    for i in range(7):
        day = (week_start + timedelta(days=i)).date()
        label = day.strftime("%a")
        week_days.append(label)

        record = next((x for x in weekly_data if x[0] == day), None)
        week_sales.append(int(record[1] or 0) if record else 0)
        week_orders.append(int(record[2] or 0) if record else 0)

    # === Statistik Harian ===
    start_of_day = datetime(today.year, today.month, today.day)
    end_of_day = start_of_day + timedelta(days=1)

    daily_sales = (
        db.session.query(func.sum(Order.total))
        .filter(Order.created_at >= start_of_day, Order.created_at < end_of_day)
        .scalar() or 0
    )
    daily_orders = (
        db.session.query(func.count(Order.id))
        .filter(Order.created_at >= start_of_day, Order.created_at < end_of_day)
        .scalar() or 0
    )

    # === Menu Terlaris ===
    top_menu = (
        db.session.query(
            MenuItem.name,
            func.sum(OrderItem.quantity).label("total_qty")
        )
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    top_menu_labels = [item.name for item in top_menu]
    top_menu_counts = [int(item.total_qty) for item in top_menu]
    menu_pairs = list(zip(top_menu_labels, top_menu_counts))

    # === Menu dengan Pendapatan Tertinggi ===
    top_revenue_menu = (
        db.session.query(
            MenuItem.name,
            func.sum(OrderItem.quantity * MenuItem.price).label("revenue")
        )
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity * MenuItem.price).desc())
        .first()
    )
    top_revenue_menu_name = top_revenue_menu.name if top_revenue_menu else "Belum ada data"
    top_revenue_amount = top_revenue_menu.revenue if top_revenue_menu else 0

    # === Rata-rata Rating Pelanggan ===
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar() or 0

    # === Pertumbuhan Penjualan (minggu ke minggu) ===
    this_week_start = today - timedelta(days=today.weekday())  # Senin minggu ini
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)

    this_week_sales = (
        db.session.query(func.sum(Order.total))
        .filter(Order.created_at >= this_week_start)
        .scalar() or 0
    )
    last_week_sales = (
        db.session.query(func.sum(Order.total))
        .filter(Order.created_at.between(last_week_start, last_week_end))
        .scalar() or 0
    )
    sales_growth = ((this_week_sales - last_week_sales) / last_week_sales * 100) if last_week_sales > 0 else 0

    # === Jam Ramai (Peak Hours) ===
    peak_hours = (
        db.session.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count")
        )
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    # Jam ramai tahun ini
    peak_year = (
        db.session.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count")
        )
        .filter(extract("year", Order.created_at) == current_year)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    peak_hours_year = [0] * 24
    for h, c in peak_year:
        peak_hours_year[int(h)] = int(c)

    # Jam ramai bulan ini
    current_month = datetime.now().month
    peak_month = (
        db.session.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count")
        )
        .filter(extract("year", Order.created_at) == current_year)
        .filter(extract("month", Order.created_at) == current_month)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    peak_hours_month = [0] * 24
    for h, c in peak_month:
        peak_hours_month[int(h)] = int(c)

    # Jam ramai minggu ini
    peak_week = (
        db.session.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count")
        )
        .filter(Order.created_at >= week_start)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    peak_hours_week = [0] * 24
    for h, c in peak_week:
        peak_hours_week[int(h)] = int(c)

    # Jam ramai hari ini
    peak_day = (
        db.session.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count")
        )
        .filter(Order.created_at >= start_of_day, Order.created_at < end_of_day)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    peak_hours_day = [0] * 24
    for h, c in peak_day:
        peak_hours_day[int(h)] = int(c)
        
    peak_hour = None
    if any(peak_hours):
        top_hour = peak_hours.index(max(peak_hours))
        peak_hour = f"{top_hour:02d}:00"

    # === Insight Cepat (teks otomatis) ===
    insight_text = (
        f"Menu paling menguntungkan bulan ini: {top_revenue_menu_name} | "
        f"Penjualan {'meningkat' if sales_growth >= 0 else 'menurun'} {abs(sales_growth):.1f}% dibanding minggu lalu | "
        f"Puncak pesanan terjadi pukul {peak_hour or '-'}"
    )

    # === Render Template ===
    return render_template(
        "pages/admin/admin_dashboard.html",
        total_orders=total_orders,
        total_sales=total_sales,
        total_users=total_users,
        total_menu=total_menu,

        years=years,
        yearly_sales=yearly_sales,
        yearly_orders=yearly_orders,

        months=months,
        monthly_sales=monthly_sales,
        monthly_orders=monthly_orders,

        week_days=week_days,
        week_sales=week_sales,
        week_orders=week_orders,

        daily_sales=daily_sales,
        daily_orders=daily_orders,

        top_menu_labels=top_menu_labels,
        top_menu_counts=top_menu_counts,
        menu_pairs=menu_pairs,

        avg_order_value=avg_order_value,
        top_revenue_menu_name=top_revenue_menu_name,
        top_revenue_amount=top_revenue_amount,
        avg_rating=avg_rating,
        sales_growth=sales_growth,
        peak_hours_year=peak_hours_year,
        peak_hours_month=peak_hours_month,
        peak_hours_week=peak_hours_week,
        peak_hours_day=peak_hours_day,
        peak_hour=peak_hour,
        insight_text=insight_text,
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

# ========================
# FEEDBACK MANAGEMENT
# ========================
from models import Feedback

@admin_bp.route("/feedback")
@login_required
def manage_feedback():
    feedbacks = (
        db.session.query(
            Feedback.id,
            Feedback.customer_name,
            Feedback.rating,
            Feedback.message,
            Feedback.created_at,
            Order.id.label("order_id")
        )
        .outerjoin(Order, Feedback.order_id == Order.id)  # gunakan LEFT JOIN
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return render_template("pages/admin/admin_feedback.html", feedbacks=feedbacks)
