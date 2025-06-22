import os
import json
from datetime import timedelta
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_mail import Mail



# Initialize Flask app directly
app = Flask(__name__, static_folder='static', template_folder='templates')



# Upload folder config
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['WTF_CSRF_ENABLED'] = False


# Core Configurations
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///swimapp.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') or 'jasnoor.tgs@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') or 'zbvqndpaegmuipjv'
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

# Session lifetime
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
mail = Mail(app)

login_manager.login_view = 'admin_login'

# Make sessions permanent across requests
@app.before_request
def make_session_permanent():
    session.permanent = True

# Import models after db is initialized
from app.models import Admin, Organizer, Swimmer

@login_manager.user_loader
def load_user(user_id):
    role = session.get('role')
    user_type = session.get('user_type')

    if role == 'organizer':
        return Organizer.query.get(int(user_id))
    elif role == 'admin':
        return Admin.query.get(int(user_id))
    elif user_type == 'swimmer':
        return Swimmer.query.get(int(user_id))

    # Default fallback: try all
    return Swimmer.query.get(int(user_id)) or \
           Organizer.query.get(int(user_id)) or \
           Admin.query.get(int(user_id))





# Inject admin name from JSON (for use in templates)
@app.context_processor
def inject_admin_name():
    try:
        with open('admin_data.json', 'r') as f:
            data = json.load(f)
            return dict(admin_name=data.get("name", "Admin"))
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(admin_name="Admin")

# Import routes last to avoid circular import issues
from app import routes