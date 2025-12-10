from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Initialize MongoDB client
client = MongoClient(MONGODB_URL, server_api=ServerApi(
   version="1", strict=True, deprecation_errors=True))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Get database instance
database = client[DATABASE_NAME]

def get_database():
    """Get MongoDB database instance"""
    return database

# Collection getters
def get_categories_collection():
    """Get categories collection"""
    return database.categories

def get_submissions_collection():
    """Get submissions collection"""
    return database.submissions

def get_questions_collection():
    """Get questions collection"""
    return database.questions

def get_evaluations_collection():
    """Get evaluations collection"""
    return database.evaluations

# Dependency for FastAPI
def get_db():
    """FastAPI dependency for database access"""
    return database

# Cleanup function
def close_database_connection():
    """Close MongoDB connection"""
    client.close()
