from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")

# Select the 'recipes' database
db = client['recipes']

# Select the 'recipe_details' collection
collection = db['recipe_details']

# Set the default image value
default_image = "static/uploads/banhmi.jpg"

# Update documents where the 'image' field does not exist
collection.update_many(
    {"image": {"$exists": False}},
    {"$set": {"image": "static/uploads/banhmi.jpg"}}
)

# Close the MongoDB client
client.close()