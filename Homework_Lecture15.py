from flask import Flask,flash,render_template,jsonify, request,url_for,redirect,session,g
from flask_babel import Babel, _
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email , Length, EqualTo, ValidationError
import sqlite3
from flask_socketio import SocketIO,emit
from flask_caching import Cache 
from dotenv import load_dotenv
import logging
import os
from werkzeug.utils import secure_filename
from flask_wtf.file import FileField, FileAllowed
from flask_mail import Mail,Message
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField,FileField
from wtforms.validators import DataRequired

load_dotenv()
app = Flask(__name__)
client = MongoClient(os.getenv('MONGO_DB_URL'))
db = client['recipes']
collection = db['recipe_details']
hovaten = db['infos']
cart = db["cart"]
app.secret_key = 'secret_key'
app.config['SECRET_KEY'] = 'your_secret_key'
chat_messages = []

mail = Mail(app)

babel = Babel(app)
app.config['LANGUAGES'] = ['en', 'vi']  # Supported languages


app.config['MAIL_SERVER']=os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
def send_upload_confirmation_email(user):
    try:
        msg = Message(_('Upload Confirmation'), sender='recipe-website@noreply.com', recipients=[user.email])
        msg.body = _('Your recipe has been uploaded!')
        mail.send(msg)
        flash(_('Mail sent!'), 'success')
    except Exception as e:
        flash(_('There was an error sending your confirmation!'), 'danger')
        flash(str(e), 'danger')
        logging.info(f"SMTP Exception: {str(e)}")

# Function to get the user's preferred language
def get_locale():
    return session.get('lang_code', 'en')  # Default to English if not set

# Set the Flask-Babel locale selector
babel.init_app(app, locale_selector=get_locale)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})
logging.basicConfig(filename='app.log', level=logging.INFO, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('./users.db')
        create_table(db)
    return db

def create_table(db):
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT)') 
    db.commit()
    cursor.close()
    
    # Check if the 'is_admin' column exists in the 'users' table
    cursor = db.cursor()
    cursor.execute('PRAGMA table_info(users)')
    columns = cursor.fetchall()
    cursor.close()

    is_admin_column_exists = any(column[1] == 'is_admin' for column in columns)

    if not is_admin_column_exists:
        # Add the 'is_admin' column to the 'users' table
        cursor = db.cursor()
        cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
        db.commit()
        cursor.close()

    # Check if the admin user exists and insert if not
    cursor = db.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', ('thanhthu',))
    admin_exists = cursor.fetchone()
    cursor.close()
    if not admin_exists:
        cursor = db.cursor()
        cursor.execute('INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)',
                       ('thanhthu', '16112004', 'luuthanhthu16112004@gmail.com', 1))  # 1 represents an admin user
        db.commit()
        cursor.close()

class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.username = None  # Set the usename here
        self.password = None  # Set the password here
        self.email = None     # Set the email here
        self.is_admin = 0
        self.cart = []

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    cursor.close()

    if user_data:
        user_id, username, password, email, is_admin = user_data
        user = User(str(user_id))
        user.username = username
        user.password = password
        user.email = email
        user.is_admin = is_admin
        return user

# Add a language switcher route
@app.route('/change_language/<string:lang_code>')
def change_language(lang_code):
    session['lang_code'] = lang_code
    return redirect(request.referrer or url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user_data = cursor.fetchone()
        cursor.close()

        if user_data:
            user_id = user_data[0]
            user = User(str(user_id))
            user.username = username
            user.password = password
            login_user(user)
            return redirect(url_for('profile'))
        else:
            flash('Login failed. Check your username or password', 'danger')

    return render_template('login.html')

@app.route('/contact_info', methods=['GET', 'POST'])
@login_required
def contact_info():
    user_id = current_user.id
    user_contact_info = hovaten.find_one({'user_id': user_id})

    if request.method == 'POST':
        form = ContactInfoForm(request.form)
        if form.validate():
            full_name = form.full_name.data
            email = form.email.data
            contact_information = form.contact_information.data

            # Check if the user's contact info already exists
            if user_contact_info:
                # Update the user's contact info
                hovaten.update_one({'user_id': user_id}, {'$set': {'full_name': full_name, 'email': email, 'contact_information': contact_information}})
            else:
                # Create a new document for user's contact info
                contact_info_data = {
                    'user_id': user_id,
                    'full_name': full_name,
                    'email': email,
                    'contact_information': contact_information
                }
                hovaten.insert_one(contact_info_data)

            return redirect(url_for('profile'))

    # If user_contact_info is None, it means the user has not filled in the info yet
    if user_contact_info:
        form = ContactInfoForm(data=user_contact_info)
    else:
        form = ContactInfoForm()

    return render_template('contact_info.html', user=current_user, form=form)

@app.route('/edit_contact_info', methods=['GET', 'POST'])
@login_required
def edit_contact_info():
    user_id = current_user.id
    user_contact_info = hovaten.find_one({'user_id': user_id})

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        contact_information = request.form['contact_information']

        # Check if the user's contact info already exists
        if user_contact_info:
            # Update the user's contact info
            hovaten.update_one({'user_id': user_id}, {'$set': {'full_name': full_name, 'email': email, 'contact_information': contact_information}})
        else:
            # Create a new document for user's contact info
            contact_info_data = {
                'user_id': user_id,
                'full_name': full_name,
                'email': email,
                'contact_information': contact_information
            }
            hovaten.insert_one(contact_info_data)

        return redirect(url_for('profile'))

    # If user_contact_info is None, it means the user has not filled in the info yet
    if user_contact_info:
        full_name = user_contact_info['full_name']
        email = user_contact_info['email']
        contact_information = user_contact_info['contact_information']
    else:
        full_name = ''
        email = ''
        contact_information = ''

    return render_template('edit_contact_info.html', full_name=full_name, email=email, contact_information=contact_information)


@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if current_user.is_authenticated and current_user.is_admin == 1:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ? AND is_admin = 1', (username, password))
        admin_data = cursor.fetchone()
        cursor.close()

        if admin_data:
            user_id = admin_data[0]
            user = User(str(user_id))
            user.username = username
            user.password = password
            user.is_admin = 1  # Set is_admin to True for admin
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Admin login failed. Check your username or password', 'danger')

    return render_template('login_admin.html')

@app.before_request
def log_request_info():
    if request.method == 'POST':
        logging.info(f"Items in Cart: {cart.find()}")
    logging.info(f"Request Method: {request.method}")
    logging.info(f"Request URL: {request.url}")
    logging.info(f"Request Headers: {dict(request.headers)}")
    logging.info(f"Request Data: {request.get_data()}")

@app.after_request
def log_response_info(response):
    if request.method == 'POST':
        logging.info(f"Items in Cart: {cart.find()}")
    logging.info(f"Response Status Code: {response.status_code}")
    logging.info(f"Response Headers: {dict(response.headers)}")
    logging.info(f"Response Data: {response.get_data()}")
    return response

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    recipes = list(collection.find())
    if current_user.is_authenticated and current_user.is_admin == 1:
        return render_template('admin_dashboard.html',user=current_user,recipes=recipes)
    else :
        return redirect(url_for('profile'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()

    if form.validate_on_submit():
        dish_name = form.dish_name.data
        description = form.description.data
        origin = form.origin.data

        # Check if the post request has the file part
        if 'image' in request.files:
            image = form.image.data

            # If the user does not select a file, the browser submits an empty file without a filename
            if image.filename != '' and allowed_file(image.filename):
                # Save the uploaded file to the specified folder
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                # Handle invalid file types or empty file
                flash('Invalid file format. Please upload an image file.', 'danger')
                return redirect(url_for('add_recipe'))

        # Continue with saving recipe details to the database
        # ...

        # Insert the recipe details into the database, including the image filename
        recipe_details = {
            'dish_name': dish_name,
            'description': description,
            'origin': origin,
            'image': filename  # Add the image filename to the recipe details
        }
        collection.insert_one(recipe_details)

        send_upload_confirmation_email(current_user)
        flash('Recipe added successfully', 'success')
        return redirect(url_for('profile'))

    return render_template('add_recipe.html', user=current_user, form=form)
@app.route('/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = collection.find_one({'_id': ObjectId(recipe_id)})

    if recipe is None:
        flash('recipe not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        origin = request.form['origin']

        collection.update_one({'_id': ObjectId(recipe_id)}, {'$set': {'name': name, 'description': description, 'origin': origin}})
        flash('recipe edited successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_recipe.html', recipe=recipe, recipe_id=recipe_id)


@app.route('/')
def home():
    recipes = list(collection.find())
    return render_template('home.html',recipes=recipes)

@app.route('/profile')
@login_required
def profile():
    recipes = list(collection.find())
    user_id = current_user.id
    user_contact_info = hovaten.find_one({'user_id': user_id})
    return render_template('profile.html', user=current_user, recipes=recipes, user_contact_info=user_contact_info)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

class RegistrationForm(FlaskForm):
    username = StringField('Username',validators=[DataRequired(),Length(min=4,max=20)])
    email = StringField('Email',validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=0)])
    confirm_password = PasswordField('Confirm Password',validators = [DataRequired(),
EqualTo('password')])
    submit = SubmitField('Signup')
    def validate_username(self, field):
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (field.data,))
        existing_user = cursor.fetchone()
        cursor.close()
        if existing_user:
            raise ValidationError('This username is already taken. Please choose a different one.')

class ContactInfoForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    contact_information = StringField('Contact Information', validators=[DataRequired()])
    
class RecipeForm(FlaskForm):
    dish_name = StringField('Dish Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    origin = StringField('Origin', validators=[DataRequired()])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])  # Add this line for the image field
    submit = SubmitField('Add Recipe')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (username, password, email))
        db.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/registration-success')
def registration_success():
    return 'Registration successful'

@app.route('/add_to_cart/<recipe_id>', methods=['POST'])
@login_required
def add_to_cart(recipe_id):
    recipe = collection.find_one({'_id': ObjectId(recipe_id)})
    existing_item = cart.find_one({"dish_name": recipe["dish_name"], "description": recipe["description"], "origin": recipe["origin"], "user_id": current_user.id})

    if not existing_item:
        # If the item doesn't exist in the cart, add it.
        cart_item = {"dish_name": recipe["dish_name"], "description": recipe["description"], "origin": recipe["origin"], "user_id": current_user.id}
        cart.insert_one(cart_item)

    return redirect(url_for("profile"))
@app.route("/cart")
@login_required
def display_cart():
    cart_recipes = cart.find({"user_id": current_user.id})
    cart_recipes = [item for item in cart_recipes]
    return render_template("cart.html", cart_recipes=cart_recipes)

@app.route('/recipe_details/<string:recipe_id>')
@login_required
def recipe_details(recipe_id):
    recipe = collection.find_one({'_id': ObjectId(recipe_id)})
    return render_template('recipe_details.html', recipe=recipe)

@app.route("/remove_from_cart/<item_id>", methods=["GET", "POST"])
@login_required
def remove_from_cart(item_id):
    cart.delete_one({"_id": ObjectId(item_id)})
    return redirect(url_for("display_cart"))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart_recipes = list(cart.find({"user_id": current_user.id}))
        cart.delete_many({"user_id": current_user.id})
        flash('Payment successful. Your order has been placed.', 'success')
        return redirect(url_for('profile'))
    cart_recipes = list(cart.find({"user_id": current_user.id}))
    total_price = sum(item["price"] for item in cart_recipes)
    total_price = round(total_price, 2)
    return render_template('checkout.html', cart_recipes=cart_recipes, total_price=total_price)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('home.html'), 404

@app.errorhandler(500)
def not_found_error(error):
    return render_template('home.html'), 500

@app.route('/showimage')
def index():
    return render_template('showimage.html')

if __name__ == '__main__':
    app.run(debug=True)