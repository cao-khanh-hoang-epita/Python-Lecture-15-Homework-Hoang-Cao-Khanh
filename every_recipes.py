from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")

# Select the 'recipes' database
db = client['recipes']

# Select the 'recipe_details' collection
collection = db['recipe_details']

# Recipes data for Vietnamese dishes
recipes_data = [
    {
        "dish_name": "Pho",
        "description": "Traditional Vietnamese noodle soup consisting of broth, rice noodles, herbs, and meat.",
        "origin": "Vietnam",
        "image": "static/uploads/pho.jpg"  # Adjust the file path accordingly
    },
    {
        "dish_name": "Banh Mi",
        "description": "Vietnamese sandwich with a French baguette filled with various ingredients like meat, vegetables, and condiments.",
        "origin": "Vietnam",
        "image": "static/uploads/banhmi.jpg"  # Adjust the file path accordingly
    },
]

# Insert recipes data into the collection
for recipe in recipes_data:
    # Check if the recipe already exists in the collection
    if collection.count_documents({"image": recipe["image"]}) == 0:
        # If it doesn't exist, insert it
        collection.insert_one(recipe)

# Close the MongoDB client
client.close()
