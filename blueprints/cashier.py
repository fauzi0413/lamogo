from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required
from extensions import db
from models import MenuItem, Order, OrderItem

cashier_bp = Blueprint("cashier", __name__, url_prefix="/cashier")

@cashier_bp.route("/dashboard")
@login_required
def dashboard():
    items = MenuItem.query.all()
    return render_template("pages/cashier/menu.html", menu=items, cart=session.get("cart", {}))

@cashier_bp.route("/cart")
@login_required
def view_cart():
    cart = session.get("cart", {})
    items, total = [], 0
    for id_str, qty in cart.items():
        item = MenuItem.query.get(int(id_str))
        if item:
            items.append({
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "qty": qty
            })
            total += item.price * qty
    return render_template("pages/cashier/cart.html", items=items, total=total)

@cashier_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    customer_name = request.form.get("customer_name")
    customer_phone = request.form.get("customer_phone")
    cart = session.get("cart", {})

    if not cart:
        flash("Keranjang kosong")
        return redirect(url_for("cashier.dashboard"))

    order = Order(customer_name=customer_name, customer_phone=customer_phone, total=0)
    db.session.add(order)
    db.session.flush()

    total = 0
    for id_str, qty in cart.items():
        item = MenuItem.query.get(int(id_str))
        if item:
            order_item = OrderItem(order_id=order.id, menu_item_id=item.id, quantity=qty)
            db.session.add(order_item)
            total += item.price * qty

    order.total = total
    db.session.commit()

    session["cart"] = {}
    flash("Pesanan berhasil dibuat")
    return redirect(url_for("cashier.dashboard"))

@cashier_bp.route("/menu")
@login_required
def menu():
    items = MenuItem.query.all()  # Ambil semua item dari database
    return render_template("pages/cashier/menu.html", menu=items)

@cashier_bp.route("/add_to_cart", methods=["POST"])
@login_required
def add_to_cart():
    menu_id = request.form.get("menu_id")
    quantity = int(request.form.get("quantity", 1))

    cart = session.get("cart", {})
    cart[menu_id] = cart.get(menu_id, 0) + quantity
    session["cart"] = cart
    flash("Item ditambahkan ke keranjang", "success")
    return redirect(url_for("cashier.menu"))

@cashier_bp.route("/orders")
@login_required
def order():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template("pages/cashier/orders.html", orders=orders)
