from flask import Flask
from extensions import db, login_manager
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ingat-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ingat.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.admin_login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import AdminUser, User
        user = AdminUser.query.get(int(user_id))
        if user:
            return user
        return User.query.get(int(user_id))

    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    with app.app_context():
        import models
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)