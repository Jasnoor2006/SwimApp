from app import app, db
from app.models import Admin
from werkzeug.security import generate_password_hash

with app.app_context():
    if not Admin.query.filter_by(username="jasnoor.tgs@gmail.com").first():
        admin = Admin(
            username="jasnoor.tgs@gmail.com",
            password=generate_password_hash("jasnoor@29")
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin created successfully.")
    else:
        print("⚠️ Admin already exists.")
