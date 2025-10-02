from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from extensions import db, socketio   # ✅ ambil dari extensions
from models import OrderItem

kitchen_bp = Blueprint("kitchen", __name__, url_prefix="/kitchen")

@kitchen_bp.route("/dashboard")
@login_required
def dashboard():
    # Semua item yang belum selesai
    items = OrderItem.query.filter(OrderItem.status.in_(["open", "cooking"])).all()
    return render_template("pages/kitchen/dashboard.html", items=items)

@kitchen_bp.route("/cooking/<int:item_id>")
@login_required
def mark_cooking(item_id):
    item = OrderItem.query.get_or_404(item_id)
    item.status = "cooking"
    db.session.commit()

    # broadcast event ke semua client
    socketio.emit("order_update", {"id": item.id, "status": "cooking"})

    flash(f"{item.menu_item.name} sedang dimasak", "info")
    return redirect(url_for("kitchen.dashboard"))

@kitchen_bp.route("/ready/<int:item_id>")
@login_required
def mark_ready(item_id):
    item = OrderItem.query.get_or_404(item_id)
    item.status = "ready"
    db.session.commit()

    # kirim detail biar waiter bisa render row baru
    socketio.emit("order_update", {
        "id": item.id,
        "order_id": item.order_id,
        "status": "ready",
        "menu_name": item.menu_item.name,
        "quantity": item.quantity
    })

    flash(f"{item.menu_item.name} sudah selesai dimasak", "success")
    return redirect(url_for("kitchen.dashboard"))
