from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv
import paypalrestsdk

db = SQLAlchemy()
DB_NAME = 'database.sqlite3'


def create_database(app):
    """Create the database if it does not exist."""
    with app.app_context():
        db.create_all()
        print('Database Created')


def create_app():
    app = Flask(__name__)
    
    # Load environment variables
    load_dotenv()

    # Configure app
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "your-default-secret-key")  # Use .env for production
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Suppress warnings

    # Initialize database
    db.init_app(app)

    # Configure PayPal
    paypalrestsdk.configure({
        "mode": "sandbox",  # Change to "live" for production
        "client_id": os.environ.get("PAYPAL_CLIENT_ID", "Ac-6BenOMQUWhSKfhyApy0Hpgmr_ZgM2dK_IHPF62ihajDu-Jxj6BKUyErxeh2n_1tSvZ-JMaWpYbPBH"),
        "client_secret": os.environ.get("PAYPAL_CLIENT_SECRET", "EGDEo0-Zf5zW8HZLGB0fG8_PLr1RqclDrA_bZHcUbU3c78TqnoIKFaZD_cnF3ZS2DRwB6tqa7I7HNZNC")
    })

    # Error handler for 404
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html'), 404

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(id):
        from .models import Customer  # Import here to avoid circular imports
        return Customer.query.get(int(id))

    # Import and register blueprints
    from .views import views
    from .auth import auth
    from .admin import admin
    from .models import Customer, Cart, Product, Order

    app.register_blueprint(views, url_prefix='/')  # localhost:5000/about-us
    app.register_blueprint(auth, url_prefix='/')    # localhost:5000/auth/change-password
    app.register_blueprint(admin, url_prefix='/')   # localhost:5000/admin

    # Create database if it doesn't exist
    create_database(app)

    return app
