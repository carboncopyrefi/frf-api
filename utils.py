from sqlmodel import Session, select
from models import Evaluation
import os, aiohttp
from dotenv import load_dotenv

load_dotenv()

def calculate_submission_score(submission_id: str, session: Session) -> float:
    """Calculate the average score of all evaluations for an submission"""
    evaluations = session.exec(
        select(Evaluation).where(Evaluation.submission_id == submission_id)
    ).all()
    
    if not evaluations:
        return None
    
    # Filter out evaluations without scores and calculate average
    valid_scores = [eval.score for eval in evaluations if eval.score is not None]
    
    if not valid_scores:
        return None
    
    # Normalize score to 0-1 range
    # Adjust this logic based on your scoring system
    max_score = float(os.getenv("MAX_SCORE"))
    normalized_scores = [min(max(score / max_score, 0.0), 1.0) for score in valid_scores]
    average_score = sum(normalized_scores) / len(normalized_scores)
    
    return round(average_score, 4)

async def get_karma_data(karma_gap_id: str):
    milestone_list = []
    update_list = []
    url = os.getenv("KARMA_GAP_API") + karma_gap_id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                details = data["details"]
                for update in data.get('updates', []):
                    item = {
                        "title": update.get('title', ''),
                        "description": update.get('text', ''),
                        "date": update.get('createdAt', ''),
                        "verified": update.get('verified', False),
                        "deliverables": update.get('deliverables', [])
                    }
                    update_list.append(item)

                return {
                    "project_details": details,
                    "updates": update_list
                }
            else:
                raise Exception(f"Failed to fetch Karma GAP data with status {response.status}")