from pymongo import MongoClient
import os

# MongoDB connection URI - supports both local and Atlas connections
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# For MongoDB Atlas, the URI should look like:
# mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority

client = MongoClient(MONGODB_URI)
db = client["trada_db"]  # Use the same database name as frontend

def get_db():
    return db
