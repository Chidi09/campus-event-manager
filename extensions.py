from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_mail import Mail
from flask_apscheduler import APScheduler

# Create extension instances
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
scheduler = APScheduler()

# Configure login behavior
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
