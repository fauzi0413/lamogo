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

def _maybe_close_order(order: Order) -> None:
    """
    Tutup order jika semua OrderItem sudah delivered/close.
    """
    allowed_done = {"delivered", "close"}         # status item yang dianggap selesai
    if all(i.status in allowed_done for i in order.items):
        if order.status != "close":
            order.status = "close"
            db.session.commit()

@waiter_bp.route("/deliver/<int:item_id>")
@login_required
def deliver_item(item_id):
    item = OrderItem.query.get_or_404(item_id)
    item.status = "delivered"
    db.session.commit()

    # cek semua item pada order; jika semua delivered/close → order close
    order = Order.query.get(item.order_id)
    _maybe_close_order(order)

    # broadcast realtime
    socketio.emit("order_update", {
        "id": item.id,
        "order_id": item.order_id,
        "status": item.status,          # "delivered"
        "order_status": order.status    # bisa "close" kalau semua selesai
    })

    flash(f"Pesanan {item.menu_item.name} berhasil diantar ✅", "success")
    return redirect(url_for("waiter.dashboard"))