from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_required
from extensions import db
from models import MenuItem, Order, OrderItem, Feedback
from sqlalchemy.orm import joinedload

import requests


cashier_bp = Blueprint("cashier", __name__, url_prefix="/cashier")

# ========================
# DASHBOARD & MENU
# ========================
@cashier_bp.route("/dashboard")
@login_required
def dashboard():
    items = MenuItem.query.filter_by(is_active=True).all()
    return render_template("pages/cashier/menu.html", menu=items, cart=session.get("cart", {}))


@cashier_bp.route("/menu")
def menu():
    menu = MenuItem.query.all()
    return render_template("pages/cashier/menu.html", menu=menu)

@cashier_bp.route("/menu/search")
def menu_search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        items = MenuItem.query.all()
    else:
        items = MenuItem.query.filter(MenuItem.name.ilike(f"%{query}%")).all()

    result = [{
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "image": item.image
    } for item in items]
    
    return jsonify(result)


# ========================
# KERANJANG
# ========================
@cashier_bp.route("/cart")
@login_required
def view_cart():
    cart = session.get("cart", {})
    items, total = [], 0
    for id_str, qty_data in cart.items():
        item = MenuItem.query.get(int(id_str))
        if item:
            # pastikan qty berupa angka
            qty = qty_data["qty"] if isinstance(qty_data, dict) else qty_data
            note = qty_data.get("note", "") if isinstance(qty_data, dict) else ""
            items.append({
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "qty": qty,
                "note": note,
            })
            total += item.price * qty

    return render_template("pages/cashier/cart.html", items=items, total=total)


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
        note = request.form.get(f"note_{key}", "").strip()
        if qty:
            qty = int(qty)
            if qty > 0:
                cart[key] = {"qty": qty, "note": note}
            else:
                cart.pop(key, None)
    session["cart"] = cart
    flash("Keranjang diperbarui", "success")
    return redirect(url_for("cashier.view_cart"))


# ========================
# CHECKOUT
# ========================
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
        status="open",
        amount_paid=int(amount_paid) if amount_paid else None,
        change_due=int(change_due) if change_due else None,
        total=0
    )
    db.session.add(order)
    db.session.flush()

    total = 0
    
    for id_str, item_data in cart.items():
        item = MenuItem.query.get(int(id_str))
        if not item:
            continue

        if isinstance(item_data, dict):
            qty = item_data.get("qty", 1)
            note = item_data.get("note", "")
        else:
            qty = int(item_data)
            note = ""

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.id,
            quantity=qty,
            price=item.price,
            status="open",
            notes=note,
        )

        db.session.add(order_item) 
        total += item.price * qty

    order.total = total
    db.session.commit()
    session["cart"] = {}

    # kirim pesan WhatsApp otomatis
    phone = customer_phone.strip().replace(" ", "")
    if phone.startswith("0"):
        phone = "62" + phone[1:]  # ubah ke format internasional

    message = create_whatsapp_message(order)
    send_fonnte_message(phone, message)

    flash("Pesanan berhasil dibuat dan struk dikirim ke WhatsApp ✅", "success")
    return redirect(url_for("cashier.dashboard"))


# ========================
# FEEDBACK (PUBLIC FORM)
# ========================
@cashier_bp.route("/feedback/<int:order_id>", methods=["GET", "POST"])
def feedback_form(order_id):
    order = Order.query.get_or_404(order_id)

    if request.method == "POST":
        rating = int(request.form.get("rating"))
        message = request.form.get("message")
        customer_name = request.form.get("customer_name") or "Anonim"

        # ✅ Jika user memilih anonim → tidak disimpan ke order_id
        if customer_name.lower() == "anonim":
            feedback = Feedback(
                order_id=None,
                customer_name="Anonim",
                rating=rating,
                message=message
            )
        else:
            feedback = Feedback(
                order_id=order.id,
                customer_name=customer_name,
                rating=rating,
                message=message
            )

        db.session.add(feedback)
        db.session.commit()

        # flash("Terima kasih atas feedback Anda!", "success")
        return redirect(url_for("cashier.thank_you"))

    return render_template("pages/feedback_form.html", order=order)


@cashier_bp.route("/feedback/thank-you")
def thank_you():
    return render_template("pages/feedback_form_respon.html")

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



# ========================
# HELPER FUNCTIONS
# ========================
def send_fonnte_message(phone, message):
    api_key = "ASk4Nsv7WSBhbjhchWkn"

    headers = {
        "Authorization": api_key
    }

    data = {
        "target": phone,
        "message": message
    }

    try:
        response = requests.post("https://api.fonnte.com/send", data=data, headers=headers)
        print("Fonnte Response:", response.text)
    except Exception as e:
        print("Gagal mengirim pesan WhatsApp:", e)


def create_whatsapp_message(order: Order):
    lines = []
    lines.append(f" *Struk Pembelian #{order.id}*")
    lines.append("")
    lines.append(f" *Nama:* {order.customer_name}")
    lines.append(f" *No. HP:* {order.customer_phone}")
    lines.append(f" *Metode:* {order.payment_method.upper()}")
    lines.append("──────────────────────")

    for item in order.items:
        subtotal = item.quantity * item.price
        lines.append(f"{item.menu_item.name} x{item.quantity} - Rp {subtotal:,.0f}".replace(",", "."))
        if item.notes:
            lines.append(f"Catatan: {item.notes}")

    lines.append("──────────────────────")
    lines.append(f" *Total:* Rp {order.total:,.0f}".replace(",", "."))
    if order.amount_paid:
        lines.append(f" *Dibayar:* Rp {order.amount_paid:,.0f}".replace(",", "."))
    if order.change_due is not None:
        lines.append(f" *Kembalian:* Rp {order.change_due:,.0f}".replace(",", "."))
    lines.append("")
    lines.append("🙏 Terima kasih telah mampir di *LAMOGO*!")

    # Tambahkan link feedback
    lines.append("")
    form_link = f"http://127.0.0.1:5000/cashier/feedback/{order.id}"  # ganti sesuai domain production nanti 
    lines.append(f"💬 Kami ingin mendengar pendapat Anda! Berikan ulasan di sini: {form_link}")
    lines.append("")
    
    return "\n".join(lines)
