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
        "origin": "Vietnam"
    },
    {
        "dish_name": "Banh Mi",
        "description": "Vietnamese sandwich with a French baguette filled with various ingredients like meat, vegetables, and condiments.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Goi Cuon",
        "description": "Fresh spring rolls filled with shrimp, herbs, pork, rice vermicelli, and other ingredients.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Bun Thit Nuong",
        "description": "Grilled pork served over vermicelli noodles with fresh herbs and a flavorful sauce.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Com tam",
        "description": "Broken rice served with grilled pork, egg, and various accompaniments.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Ca Kho To",
        "description": "Caramelized fish in clay pot, a popular Vietnamese braised fish dish.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Cha Ca Thang Long",
        "description": "Turmeric-seasoned fish sautéed with dill and other herbs, often served with rice noodles.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Bun Bo Hue",
        "description": "Spicy beef noodle soup with lemongrass and other aromatic herbs.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Cao Lau",
        "description": "Regional Vietnamese dish with noodles, pork, and local greens, distinctive to Hoi An.",
        "origin": "Vietnam"
    },
    {
        "dish_name": "Xoi Xeo",
        "description": "Sticky rice with mung bean paste and fried shallots, often served with pork or chicken.",
        "origin": "Vietnam"
    }
]

# Insert recipes data into the collection
for recipe in recipes_data:
    # Check if the recipe already exists in the collection
    if collection.count_documents({"dish_name": recipe["dish_name"]}) == 0:
        # If it doesn't exist, insert it
        collection.insert_one(recipe)

# Close the MongoDB client
client.close()
