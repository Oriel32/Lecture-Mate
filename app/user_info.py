from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()

class User:  
    def __init__(self, user_id = "user123", session = 0):
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.user_id = user_id
        self.session = session
        self.user_date, self.sessions = self.get_db_data()
        
    def get_db_data(self):
        if not self.mongodb_uri:
            print("MongoDB URI is not provided in environment variables.")
            return

        try:
            # Connect to MongoDB
            client = MongoClient(self.mongodb_uri)
            db = client["mydb"]
            collection = db["transcripts"]

            # Check if the user ID exists
            user_data = collection.find_one({"user_id": self.user_id})
            if session == 0:
                session = 
          