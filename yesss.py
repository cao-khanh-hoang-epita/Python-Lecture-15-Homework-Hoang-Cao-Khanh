import sqlite3
from flask import Flask, g, request
from dotenv import load_dotenv
import os
from flask_babel import Babel, lazy_gettext as _l
from flask_login import LoginManager, UserMixin
from flask_mail import Mail


load_dotenv()
app = Flask(_name_)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['LANGUAGES'] = {
    'en': 'English',
    'fr': 'French'
}
login_manager = LoginManager()
login_manager.login_view = "authentication.login"
login_manager.login_message = _l('Please log in to access this page.')
login_manager.init_app(app)

app.config['MAIL_SERVER']=os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

class User(UserMixin):
    def _init_(self, id, username, password, email):
        self.id = id
        self.username = username
        self.password = password
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user[0], user[1], user[2], user[3])
    else:
        return None

def get_db():
    db = getattr(g, '_users_database', None)
    if db is None:
        db = g._users_database = sqlite3.connect('./users.db')
        create_table(db)
    return db

def create_table(db):
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, email TEXT)') 
    db.commit()
    cursor.close()
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys(), 'en')

babel = Babel(app)
babel.init_app(app, locale_selector=get_locale)

@app.teardown_appcontext
def close_connection(exception):
    db1 = getattr(g, '_users_database', None)
    if db1 is not None:
        db1.close()
    db2 = getattr(g, '_file_database', None)
    if db2 is not None:
        db2.close()
        
if _name_ == '_main_':
    from authentication import authentication
    from recipes import recipes
    app.register_blueprint(authentication, url_prefix='/authentication')
    app.register_blueprint(recipes, url_prefix='/recipes')
    app.run()