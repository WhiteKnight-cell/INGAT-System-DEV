import os
from pathlib import Path
from datetime import timedelta
from flask import Flask, redirect, url_for, request
from extensions import db, login_manager
from dotenv import load_dotenv

# Load environmental configurations properly before bootstrap initializing
load_dotenv(Path(__file__).resolve().parent / '.env', override=True)

def seed_default_agencies():
    from models import Agency

    if Agency.query.count() > 0:
        return

    agencies = [
        Agency(
            agency_name='DENR-EMB',
            contact_email='records@emb.gov.ph',
            contact_number='0289202246',
            violation_types='Illegal Dumping,Air Pollution,Water Pollution,Toxic Waste',
        ),
        Agency(
            agency_name='BFAR',
            contact_email='info@bfar.da.gov.ph',
            contact_number='0289298074',
            violation_types='Illegal Fishing,Marine Habitat Destruction,Poaching',
        ),
        Agency(
            agency_name='DENR-FMB',
            contact_email='fmb@denr.gov.ph',
            contact_number='0289274788',
            violation_types='Illegal Logging,Unauthorized Timber Transport,Kaingin',
        ),
        Agency(
            agency_name='LLDA',
            contact_email='info@llda.gov.ph',
            contact_number='0283764039',
            violation_types='Industrial Water Pollution,Illegal Reclamation',
        ),
    ]
    for agency in agencies:
        db.session.add(agency)
    db.session.commit()


def seed_default_admin():
    from models import AdminUser

    admin_email = os.getenv('ADMIN_EMAIL', 'admin@ingat.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@1234')

    if AdminUser.query.filter_by(email=admin_email).first():
        return

    admin = AdminUser(email=admin_email)
    admin.set_password(admin_password) # Fixed to use our updated model hashing helper function
    
    db.session.add(admin)
    db.session.commit()


def _migrate_user_columns():
    from sqlalchemy import inspect as sa_inspect
    from models import User

    inspector = sa_inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('users')]
    additions = []

    if 'default_lang' not in columns:
        additions.append("ALTER TABLE users ADD COLUMN default_lang VARCHAR(10) DEFAULT 'en-US'")

    for stmt in additions:
        db.session.execute(db.text(stmt))
    db.session.commit()


def _migrate_admin_columns():
    from sqlalchemy import inspect as sa_inspect
    from models import AdminUser

    inspector = sa_inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('admin_users')]
    additions = []

    if 'email_notif' not in columns:
        additions.append('ALTER TABLE admin_users ADD COLUMN email_notif BOOLEAN DEFAULT 1')
    if 'inapp_notif' not in columns:
        additions.append('ALTER TABLE admin_users ADD COLUMN inapp_notif BOOLEAN DEFAULT 1')
    if 'session_token' not in columns:
        additions.append('ALTER TABLE admin_users ADD COLUMN session_token VARCHAR(64) DEFAULT NULL')

    for stmt in additions:
        db.session.execute(db.text(stmt))

    # Seed session_token for existing admins that have NULL
    db.session.execute(
        db.text("UPDATE admin_users SET session_token = :token WHERE session_token IS NULL"),
        {'token': __import__('secrets').token_hex(32)}
    )
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ingat-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ingat.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

    # Initialize extensions context matching state configurations
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'user.user_login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import AdminUser, User

        if isinstance(user_id, str) and '-' in user_id:
            role, raw_id = user_id.split('-', 1)
            try:
                if role == 'admin':
                    return AdminUser.query.get(int(raw_id))
                if role == 'user':
                    return User.query.get(int(raw_id))
            except ValueError:
                return None

        # Fallback safe parser if string integer IDs are received directly
        try:
            target_id = int(user_id)
            user = AdminUser.query.get(target_id)
            if user:
                return user
            return User.query.get(target_id)
        except ValueError:
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/admin'):
            return redirect(url_for('admin.admin_login'))
        return redirect(url_for('user.user_login'))

    # Import and register blueprints securely within application workspace factory
    from routes.admin_routes import admin_bp
    from routes.user_routes import user_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    @app.route('/')
    def index():
        return redirect(url_for('user.user_login'))

    # Build active connection database tables schemas 
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        _migrate_admin_columns()
        _migrate_user_columns()
        seed_default_admin()
        seed_default_agencies()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)