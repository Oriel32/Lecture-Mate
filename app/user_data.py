from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()

class User:  
    def __init__(self, user_id = "user123"):
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.user_id = user_id
        self.user_data = self.get_user_data()
        self.session_id = None
        self.session_data = None
        
    def get_user_data(self):
        if not self.mongodb_uri:
            print("MongoDB URI is not provided in environment variables.")
            return

        try:
            # Connect to MongoDB
            client = MongoClient(self.mongodb_uri)
            db = client["mydb"]
            collection = db["transcripts"]

            # Find user in collection
            user_data = collection.find_one({"user_id": self.user_id})
            
            if user_data:
                return user_data
            else:
                self.session_id = 1
                return None
                
        except Exception as e:
            print("Error accessing to MongoDB:", e)

    def user_info(self):
        if self.user_data:
            grades = [session["grades"] for session in self.user_data.get("sessions", [])]
        return self.user_id, grades

    def set_session_data(self, session_id):
        if self.user_data:
                existing_session = next(
                        (session for session in self.user_data.get("sessions", []) if session["session_id"] == session_id),
                        None
                    )
                if existing_session:
                    self.session_id = session_id
                    self.session_data = existing_session
                    print(f"session {session_id} exist for user {self.user_id}")
                    return existing_session
                else:
                    self.session_id = max([session["session_id"] for session in self.user_data.get("sessions", [])], default=0) + 1
                    print(f"new session - {self.session_id} for user {self.user_id}")
        else:
            self.session_id = 1
            print(f"first session for user {self.user_id}")
        return None
            
    def save_session_to_mongodb(self, new_session_data):
        try:
            # Connect to MongoDB
            client = MongoClient(self.mongodb_uri)
            db = client["mydb"]
            collection = db["transcripts"]
            
            if self.session_data:
                # Append new data to the existing session
                if new_session_data["session_topic"] != None:
                    self.session_data["session_topic"] = new_session_data["session_topic"]
                self.session_data["questions"].extend(new_session_data["questions"])
                self.session_data["answers"].extend(new_session_data["answers"])
                self.session_data["feedbacks"].extend(new_session_data["feedbacks"])
                self.session_data["grades"].extend(new_session_data["grades"])
                self.session_data["transcript"].update(new_session_data["transcript"])

                # Update the session in the database
                collection.update_one(
                    {"user_id": self.user_id, "sessions.session_id": self.session_id},
                    {"$set": {"sessions.$": self.session_data}}
                )
                print(f"Session updated for user_id: {self.user_id}, session_id: {self.session_id}")
            else:
                # Add a new session to the user's sessions array
                collection.update_one(
                    {"user_id": self.user_id},
                    {"$push": {"sessions": new_session_data}},
                    upsert=True  # If the user doesn't exist, insert a new document
                )
                print(f"New session added for user_id: {self.user_id}, session_id: {self.session_id}")
                
        except Exception as e:
            print("Error saving transcript to MongoDB:", e)