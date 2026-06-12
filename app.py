from pathlib import Path
from flask import Flask, redirect, request, url_for
from extensions import db, login_manager
from dotenv import load_dotenv
import os

# Always load project-root .env (override stale shell placeholders).
load_dotenv(Path(__file__).resolve().parent / '.env', override=True)


def seed_default_agencies():
    from models import Agency

    if Agency.query.count() > 0:
        return

    agencies = [
        Agency(
            agency_name='DENR',
            contact_email='denr@gov.ph',
            contact_number='09171234567',
            violation_types='Air Pollution,Illegal Logging',
        ),
        Agency(
            agency_name='LLDA',
            contact_email='llda@gov.ph',
            contact_number='09181234567',
            violation_types='Water Pollution',
        ),
        Agency(
            agency_name='LGU',
            contact_email='lgu@gov.ph',
            contact_number='09191234567',
            violation_types='Illegal Dumping,Others',
        ),
    ]
    for agency in agencies:
        db.session.add(agency)
    db.session.commit()


def seed_default_agencies():
    from models import Agency

    if Agency.query.count() > 0:
        return

    agencies = [
        Agency(
            agency_name='DENR',
            contact_email='denr@gov.ph',
            contact_number='09171234567',
            violation_types='Air Pollution,Illegal Logging',
        ),
        Agency(
            agency_name='LLDA',
            contact_email='llda@gov.ph',
            contact_number='09181234567',
            violation_types='Water Pollution',
        ),
        Agency(
            agency_name='LGU',
            contact_email='lgu@gov.ph',
            contact_number='09191234567',
            violation_types='Illegal Dumping,Others',
        ),
    ]
    for agency in agencies:
        db.session.add(agency)
    db.session.commit()


def seed_default_admin():
    from models import AdminUser
    from werkzeug.security import generate_password_hash

    admin_email = os.getenv('ADMIN_EMAIL', 'admin@ingat.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@1234')

    if AdminUser.query.filter_by(email=admin_email).first():
        return

    db.session.add(AdminUser(
        email=admin_email,
        password_hash=generate_password_hash(admin_password),
    ))
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ingat-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ingat.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'user.user_login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import AdminUser, User

        if isinstance(user_id, str) and '-' in user_id:
            role, raw_id = user_id.split('-', 1)
            if role == 'admin':
                return AdminUser.query.get(int(raw_id))
            if role == 'user':
                return User.query.get(int(raw_id))

        user = AdminUser.query.get(int(user_id))
        if user:
            return user
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/admin'):
            return redirect(url_for('admin.admin_login'))
        return redirect(url_for('user.user_login'))

    from routes.admin_routes import admin_bp
    from routes.user_routes import user_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    @app.route('/')
    def index():
        return redirect(url_for('user.user_login'))

    with app.app_context():
        import models  # noqa: F401
        db.create_all()


        seed_default_admin()

        seed_default_agencies()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
