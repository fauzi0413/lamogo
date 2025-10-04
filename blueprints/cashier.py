# update 3 Oktober 2025 - testing commit terdeteksi

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_required
from extensions import db
from models import MenuItem, Order, OrderItem
from sqlalchemy.orm import joinedload
from urllib.parse import quote

cashier_bp = Blueprint("cashier", __name__, url_prefix="/cashier")

@cashier_bp.route("/dashboard")
@login_required
def dashboard():
    items = MenuItem.query.filter_by(is_active=True).all()
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
    payment_method = request.form.get("payment_method")
    amount_paid = request.form.get("amount_paid")
    change_due = request.form.get("change_due")

    cart = session.get("cart", {})

    if not cart:
        flash("Keranjang kosong", "warning")
        return redirect(url_for("cashier.dashboard"))

    order = Order(
        customer_name=customer_name,
        customer_phone=customer_phone,
        payment_method=payment_method,
        status="open",  # status varchar → open, pending, close
        amount_paid=int(amount_paid) if amount_paid else None,
        change_due=int(change_due) if change_due else None,
        total=0
    )
    db.session.add(order)
    db.session.flush()  # ambil ID dulu

    total = 0
    for id_str, qty in cart.items():
        item = MenuItem.query.get(int(id_str))
        if item:
            db.session.add(OrderItem(
                order_id=order.id,
                menu_item_id=item.id,
                quantity=qty,
                price=item.price,    # simpan harga saat transaksi
                status="open"     # default untuk dapur/waiter
            ))
            total += item.price * qty

    order.total = total
    db.session.commit()

    session["cart"] = {}
    flash("Pesanan berhasil dibuat", "success")
    return redirect(url_for("cashier.dashboard"))

@cashier_bp.route("/menu")
@login_required
def menu():
    query = request.args.get("q", "")
    if query:
        items = MenuItem.query.filter(
            (MenuItem.name.ilike(f"%{query}%")) | 
            (MenuItem.description.ilike(f"%{query}%")),
            MenuItem.is_active == True
        ).all()
    else:
        items = MenuItem.query.filter_by(is_active=True).all()
    return render_template("pages/cashier/menu.html", menu=items)

@cashier_bp.route("/menu/search")
@login_required
def search_menu():
    query = request.args.get("q", "")
    if query:
        items = MenuItem.query.filter(
            (MenuItem.name.ilike(f"%{query}%")) |
            (MenuItem.description.ilike(f"%{query}%")),
            MenuItem.is_active == True
        ).all()
    else:
        items = MenuItem.query.filter_by(is_active=True).all()

    results = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": f"{item.price:,.0f}",
            "image": item.image
        }
        for item in items
    ]
    return jsonify(results)

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

@cashier_bp.route("/remove_from_cart/<int:item_id>")
@login_required
def remove_from_cart(item_id):
    cart = session.get("cart", {})
    cart.pop(str(item_id), None)
    session["cart"] = cart
    flash("Item dihapus dari keranjang", "info")
    return redirect(url_for("cashier.view_cart"))

@cashier_bp.route("/update_cart", methods=["POST"])
@login_required
def update_cart():
    cart = session.get("cart", {})
    for key in list(cart.keys()):
        qty = request.form.get(f"qty_{key}")
        if qty:
            qty = int(qty)
            if qty > 0:
                cart[key] = qty
            else:
                cart.pop(key, None)
    session["cart"] = cart
    flash("Keranjang diperbarui", "success")
    return redirect(url_for("cashier.view_cart"))

@cashier_bp.route("/orders")
@login_required
def order():
    orders = (
        Order.query
        .options(joinedload(Order.items).joinedload(OrderItem.menu_item))
        .order_by(Order.id.desc())
        .all()
    )
    return render_template("pages/cashier/orders.html", orders=orders)

