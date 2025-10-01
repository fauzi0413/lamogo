"""
LAMOGO - Simple Food Ordering Web App
Language: Python (Flask)

Cara menjalankan:
1. Pastikan Flask sudah terinstall: pip install flask
2. Simpan file ini sebagai lamogo_app.py
3. Jalankan: python lamogo_app.py
4. Buka di browser: http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from datetime import datetime

# ---------------- Konfigurasi ----------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "lamogo.db")

SECRET_KEY = "ganti-dengan-secret-key"
ADMIN_PASSWORD = "admin123"  # default admin password

app = Flask(__name__, static_url_path="/static")
app.config["SECRET_KEY"] = SECRET_KEY


# ---------------- Database ----------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            items TEXT,
            total REAL,
            created_at TEXT
        )
    """
    )
    db.commit()


def seed_data():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as c FROM menu")
    if cur.fetchone()["c"] == 0:
        items = [
            ("Nasi Goreng Lamogo", "Nasi goreng spesial ala Lamogo", 25000, "nasigoreng.jpg"),
            ("Lele Terbang", "Lele goreng kriuk khas Lamongan", 28000, "lamongan.jpg"),
            ("Es Teh Manis", "Segelas es teh manis dingin", 5000, "es_teh.jpg"),
            ("Pecel Ayam", "Ayam goreng dengan sambal khas Lamogo", 27000, "pecelayam.jpg"),
            ("Bebek Goreng", "Bebek goreng gurih dengan sambal korek", 30000, "bebek.jpg"),
            ("Soto Lamongan", "Soto ayam khas Lamongan dengan koya", 25000, "soto.jpg"),
            ("Tahu Tempe", "Tahu tempe goreng gurih", 10000, "tahu_tempe.jpg"),
            ("Rawon Lamongan", "Rawon daging dengan kuah hitam khas", 32000, "rawon.jpg"),
            ("Es Jeruk Segar", "Segelas es jeruk peras segar", 7000, "es_jeruk.jpg"),
        ]
        cur.executemany(
            "INSERT INTO menu (name, description, price, image) VALUES (?,?,?,?)", items
        )
        db.commit()



# ---------------- Helper ----------------
def cart_count():
    c = 0
    cart = session.get("cart", {})
    for v in cart.values():
        c += v
    return c


@app.context_processor
def inject_globals():
    return {"year": datetime.now().year, "cart_count": cart_count()}


# ---------------- Routes ----------------
@app.route("/")
def index():
    db = get_db()
    cur = db.execute("SELECT * FROM menu")
    menu = cur.fetchall()
    return render_template("index.html", menu=menu)


@app.route("/add_to_cart/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):
    qty = int(request.form.get("qty", 1))
    cart = session.get("cart", {})
    cart[str(item_id)] = cart.get(str(item_id), 0) + qty
    session["cart"] = cart
    flash("Item ditambahkan ke keranjang")
    return redirect(url_for("index"))


@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    items = []
    total = 0
    if cart:
        db = get_db()
        for id_str, qty in cart.items():
            cur = db.execute("SELECT * FROM menu WHERE id=?", (int(id_str),))
            row = cur.fetchone()
            if row:
                items.append(
                    {"id": row["id"], "name": row["name"], "price": row["price"], "qty": qty}
                )
                total += row["price"] * qty
    return render_template("cart.html", cart=items, total=total)


@app.route("/update_cart", methods=["POST"])
def update_cart():
    cart = session.get("cart", {})
    new_cart = {}
    for key, qty in cart.items():
        form_key = f"qty_{key}"
        if form_key in request.form:
            new_qty = int(request.form.get(form_key, 1))
            if new_qty > 0:
                new_cart[key] = new_qty
    session["cart"] = new_cart
    flash("Cart diperbarui")
    return redirect(url_for("view_cart"))


@app.route("/remove/<int:item_id>")
def remove_from_cart(item_id):
    cart = session.get("cart", {})
    key = str(item_id)
    if key in cart:
        del cart[key]
        session["cart"] = cart
    flash("Item dihapus")
    return redirect(url_for("view_cart"))


@app.route("/checkout")
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Keranjang kosong")
        return redirect(url_for("index"))
    db = get_db()
    items = []
    total = 0
    for id_str, qty in cart.items():
        cur = db.execute("SELECT * FROM menu WHERE id=?", (int(id_str),))
        row = cur.fetchone()
        if row:
            items.append({"name": row["name"], "price": row["price"], "qty": qty})
            total += row["price"] * qty
    return render_template("checkout.html", cart=items, total=total)

@app.route("/payment/<int:order_id>", methods=["GET", "POST"])
def payment(order_id):
    db = get_db()
    cur = db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    order = cur.fetchone()
    if not order:
        flash("Pesanan tidak ditemukan")
        return redirect(url_for("index"))

    if request.method == "POST":
        method = request.form.get("payment_method")
        # Simpan metode pembayaran ke database (opsional)
        db.execute("UPDATE orders SET items = items || ' [Bayar via ' || ? || ']' WHERE id=?", (method, order_id))
        db.commit()
        return render_template("order_success.html", order_id=order_id, total=order["total"])

    return render_template("payment.html", order=order)



@app.route("/place_order", methods=["POST"])
def place_order():
    cart = session.get("cart", {})
    if not cart:
        flash("Keranjang kosong")
        return redirect(url_for("index"))
    customer_name = request.form.get("customer_name")
    customer_phone = request.form.get("customer_phone")
    db = get_db()
    items = []
    total = 0
    for id_str, qty in cart.items():
        cur = db.execute("SELECT * FROM menu WHERE id=?", (int(id_str),))
        row = cur.fetchone()
        if row:
            items.append(f"{row['name']} x{qty}")
            total += row["price"] * qty
    items_text = "; ".join(items)
    cur = db.cursor()
    cur.execute(
        "INSERT INTO orders (customer_name, customer_phone, items, total, created_at) VALUES (?,?,?,?,?)",
        (customer_name, customer_phone, items_text, total, datetime.now().isoformat()),
    )
    db.commit()
    order_id = cur.lastrowid
    session["cart"] = {}
    # redirect ke halaman pembayaran
    return redirect(url_for("payment", order_id=order_id))



# ---------------- Admin ----------------
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin"))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        pw = request.form.get("password")
        if pw == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            flash("Password salah")
            return redirect(url_for("admin"))
    return render_template("admin_login.html")


@app.route("/admin/panel")
@admin_required
def admin_panel():
    db = get_db()
    cur = db.execute("SELECT * FROM menu")
    menu = cur.fetchall()
    return render_template("admin_panel.html", menu=menu)


@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def admin_add():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        db = get_db()
        db.execute(
            "INSERT INTO menu (name, description, price) VALUES (?,?,?)",
            (name, description, price),
        )
        db.commit()
        flash("Menu ditambahkan")
        return redirect(url_for("admin_panel"))
    return render_template("admin_add.html")


@app.route("/admin/edit/<int:item_id>", methods=["GET", "POST"])
@admin_required
def admin_edit(item_id):
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = float(request.form.get("price"))
        db.execute(
            "UPDATE menu SET name=?, description=?, price=? WHERE id=?",
            (name, description, price, item_id),
        )
        db.commit()
        flash("Menu diperbarui")
        return redirect(url_for("admin_panel"))
    cur = db.execute("SELECT * FROM menu WHERE id=?", (item_id,))
    item = cur.fetchone()
    return render_template("admin_edit.html", item=item)


@app.route("/admin/delete/<int:item_id>")
@admin_required
def admin_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM menu WHERE id=?", (item_id,))
    db.commit()
    flash("Menu dihapus")
    return redirect(url_for("admin_panel"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logout admin berhasil")
    return redirect(url_for("index"))


# ---------------- Run ----------------
if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_data()
    app.run(debug=True)
