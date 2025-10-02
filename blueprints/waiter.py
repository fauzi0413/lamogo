from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from extensions import db, socketio   # ambil socketio dari extensions
from models import Order, OrderItem

waiter_bp = Blueprint("waiter", __name__, url_prefix="/waiter")

@waiter_bp.route("/dashboard")
@login_required
def dashboard():
    # Ambil semua item yang sudah ready, tapi belum delivered
    items = OrderItem.query.filter(OrderItem.status == "ready").all()
    return render_template("pages/waiter/dashboard.html", items=items)

@waiter_bp.route("/deliver/<int:item_id>")
@login_required
def deliver_item(item_id):
    item = OrderItem.query.get_or_404(item_id)
    item.status = "delivered"
    db.session.commit()

    # cek kalau semua item dalam order sudah delivered → update order ke close
    order = Order.query.get(item.order_id)
    if all(i.status == "delivered" for i in order.items):
        order.status = "close"
        db.session.commit()

    # 🔥 kirim event realtime ke semua client
    socketio.emit("order_update", {
        "id": item.id,
        "order_id": item.order_id,
        "status": "delivered",
        "order_status": order.status
    })

    flash(f"Pesanan {item.menu_item.name} berhasil diantar ✅", "success")
    return redirect(url_for("waiter.dashboard"))
