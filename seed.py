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
            role="admin"  # role varchar (admin, cashier, waiter, kitchen)
        )
        admin.set_password("admin123")   # password default
        db.session.add(admin)
        print("[+] Admin user ditambahkan.")
    else:
        print("[i] Admin user sudah ada.")
        
    # Simpan perubahan
    db.session.commit()
    print("✅ Seeding selesai.")
