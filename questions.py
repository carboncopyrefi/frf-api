import json, uuid
from db import get_db, get_questions_collection

def load_questions_from_json():
    """Load questions from JSON file on startup"""
    try:
        with open('questions.json', 'r') as f:
            questions_data = json.load(f)
        
        db = get_db()
        questions_collection = get_questions_collection()
        
        # Check if questions already exist
        count = questions_collection.count_documents({})
        if count > 0:
            print(f"Found {count} existing questions, skipping import")
            return
        
        # Add IDs to questions and load them
        questions_with_ids = []
        for question_data in questions_data:
            question_data['id'] = str(uuid.uuid4())
            questions_with_ids.append(question_data)
        
        if questions_with_ids:
            questions_collection.insert_many(questions_with_ids)
            print(f"Loaded {len(questions_with_ids)} questions from JSON file")
            
    except FileNotFoundError:
        print("questions.json file not found. Please create it with your questions.")
    except Exception as e:
        print(f"Error loading questions: {e}")


# Load questions from JSON file if they don't exist
load_questions_from_json()