import logging
import sqlite3
from flask import g, redirect, render_template, request, url_for, flash
from flask_login import login_required, current_user
from flask_mail import Message
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length
from flask_babel import _, lazy_gettext as _l
from elasticsearch import Elasticsearch
import sys

from . import recipes
sys.path.append('..')
from recipe_app import mail

load_dotenv()

class RecipeForm(FlaskForm):
    title = StringField(_l('Title'), validators=[DataRequired(), Length(min=2, max=50)])
    image = FileField(_l('Image'), validators=[FileRequired()])
    cuisine = StringField(_l('Cuisine'), validators=[DataRequired(), Length(min=2, max=50)])
    ingredients = StringField(_l('Ingredients'), validators=[DataRequired(), Length(min=2, max=50)])
    instructions = TextAreaField(_l('Instructions'), validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField(_l('Submit'))

def get_db():
    db = getattr(g, '_file_database', None)
    if db is None:
        db = g._file_database = sqlite3.connect('./images.db')
        create_table(db)
    return db

def create_table(db):
    cursor = db.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS recipe_images (recipe_title TEXT, image_name TEXT, image BLOB)')
    db.commit()
    cursor.close()

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

client = MongoClient(os.getenv('MONGO_URI'))
db = client['recipe_website_db']
recipes_collection = db['recipes']

es = Elasticsearch([
    {'host': 'localhost', 'port': 9200, 'scheme':'https'}],
    verify_certs=False, basic_auth=(os.getenv('ELASTICSEARCH_USERNAME'), os.getenv('ELASTICSEARCH_PASSWORD'))
    )

# Route: /home
# Methods: GET, POST
# Requires login
# This route displays all recipes. If a POST request is made, it performs a search for recipes based on the query provided in the form.
# It also handles the retrieval of images associated with each recipe from a SQLite database and saves them to a static directory.
@recipes.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    recipes = list(recipes_collection.find())
    if request.method == 'POST':
        es.indices.create(index='recipes', ignore=400)
        for recipe in recipes:
            recipe['mongo_id'] = str(recipe.pop('_id'))
            es.index(index='recipes', id=recipe['mongo_id'], body=recipe)
        query = request.form.get('search')
        if query:
            results = es.search(index='recipes', body={'query': {'multi_match': {'query': query, 'fields': ['title', 'ingredients', 'cuisine']}}})
            recipe_ids = [ result['_id'] for result in results['hits']['hits'] ]
            recipes = [ recipes_collection.find_one({'_id': ObjectId(r_id)}) for r_id in recipe_ids ]
    image_names = [ recipe['image_name'] for recipe in recipes ]
    images = []
    db = get_db()
    cursor = db.cursor()
    for image_name in image_names:
        cursor.execute('SELECT image FROM recipe_images WHERE image_name = ?', (image_name,))
        image = cursor.fetchone()
        images.append(image)
    cursor.close()
    for image_name, image in zip(image_names, images):
        with open(os.path.join(os.getcwd(), 'recipe_website/recipes/static', image_name), 'wb') as f:
            f.write(image[0])
    recipe_images = zip(recipes, image_names)
    return render_template('home.html', recipe_images=recipe_images, user_id=current_user.id)

# Route: /create_recipe
# Methods: GET, POST
# Requires login
# This route displays a form to create a new recipe. If a POST request is made, it validates the form and inserts the new recipe into the MongoDB collection.
# It also inserts the associated image into a SQLite database and sends a confirmation email to the user.
@recipes.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        title = form.title.data
        image = form.image.data
        image_name = image.filename
        cuisine = form.cuisine.data
        ingredients = form.ingredients.data
        instructions = form.instructions.data
        recipes_collection.insert_one({
            'title': title,
            'cuisine': cuisine,
            'image_name': image_name, 
            'ingredients': ingredients, 
            'instructions': instructions, 
            'author': current_user.username,
            'author_id': current_user.id
            })
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO recipe_images (recipe_title, image_name, image) VALUES (?, ?, ?)', (title, image_name, image.read()))
        db.commit()
        cursor.close()
        send_upload_confirmation_email(current_user)
        return redirect(url_for('recipes.home'))
    return render_template('create_recipe.html', form=form)

# Route: /delete_recipe/<recipe_id>
# Method: GET
# Requires login
# This route deletes a recipe with the given ID from the MongoDB collection.
# It also deletes the associated image from the SQLite database and the static directory, and displays a flash message to confirm the deletion.
@recipes.route('/delete_recipe/<recipe_id>')
@login_required
def delete_recipe(recipe_id):
    recipe = recipes_collection.find_one({'_id': ObjectId(recipe_id)})
    image_name = recipe['image_name']
    recipes_collection.delete_one({'_id': ObjectId(recipe_id)})
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM recipe_images WHERE image_name = ?', (image_name,))
    db.commit()
    cursor.close()
    os.remove(os.path.join(os.getcwd(), 'recipe_website/recipes/static', image_name))
    flash(_('Recipe deleted successfully'), 'success')
    return redirect(url_for('recipes.home'))