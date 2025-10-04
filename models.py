from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# ===============================
# USER MODEL
# ===============================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="cashier")  
    # role: "admin", "cashier", "waiter", "kitchen"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ===============================
# MENU MODEL
# ===============================
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)


# ===============================
# ORDER MODEL
# ===============================
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    total = db.Column(db.Integer)
    payment_method = db.Column(db.String(50), nullable=True)  
    # payment_method: "cash", "qris", dll
    status = db.Column(db.String(20), default="open")  
    # status: "on progress", "open", "served", "closed"
    amount_paid = db.Column(db.Integer, nullable=True)
    change_due = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    items = db.relationship("OrderItem", backref="order", lazy=True)


# ===============================
# ORDER ITEM MODEL
# ===============================
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_item.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # harga saat transaksi (biar ga ikut berubah kalau harga menu berubah)
    status = db.Column(db.String(20), default="pending")  
    # status: "pending", "cooking", "ready", "delivered"
    notes = db.Column(db.Text, nullable=True)  # catatan tambahan (misal: pedas, tanpa es)

    menu_item = db.relationship("MenuItem", backref="order_items")
