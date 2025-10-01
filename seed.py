from app import create_app
from extensions import db
from models import User, Role, MenuItem

app = create_app()

with app.app_context():
    # === 1. Tambahkan admin user ===
    admin_email = "admin@lamogo.com"
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            name="Admin",
            email=admin_email,
            role=Role.ADMIN
        )
        admin.set_password("admin123")   # password default
        db.session.add(admin)
        print("[+] Admin user ditambahkan.")
    else:
        print("[i] Admin user sudah ada.")

    # === 2. Tambahkan menu contoh ===
    sample_menu = [
        {"name": "Nasi Goreng Lamogo", "description": "Nasi goreng spesial ala Lamogo", "price": 25000, "image": "nasigoreng.jpg"},
        {"name": "Lele Terbang", "description": "Lele goreng kriuk khas Lamongan", "price": 28000, "image": "lele.jpg"},
        {"name": "Es Teh Manis", "description": "Segelas es teh manis dingin", "price": 5000, "image": "esteh.jpg"},
        {"name": "Soto Lamongan", "description": "Soto ayam khas Lamongan dengan koya", "price": 25000, "image": "soto.jpg"},
    ]

    for item in sample_menu:
        exists = MenuItem.query.filter_by(name=item["name"]).first()
        if not exists:
            m = MenuItem(**item)
            db.session.add(m)
            print(f"[+] Menu '{item['name']}' ditambahkan.")
        else:
            print(f"[i] Menu '{item['name']}' sudah ada.")

    # Simpan perubahan
    db.session.commit()
    print("✅ Seeding selesai.")
