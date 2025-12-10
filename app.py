from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, AsyncGenerator
import json, os, utils
from datetime import datetime, timezone
import uuid

# MongoDB imports - using pymongo directly
from db import (
    get_db, get_categories_collection, get_submissions_collection, 
    get_questions_collection, get_evaluations_collection, close_database_connection
)

# Schema imports (for API responses)
from schemas import (
    CategoryCreate, CategoryRead, CategoryReadWithSubmissions,
    SubmissionCreate, SubmissionWithAnswersRead, SubmissionRead,
    EvaluationCreate, EvaluationWithAnswersRead,
    QuestionCreate, QuestionRead,
    SubmissionAnswerRead, EvaluationAnswerRead
)

# Model imports (for internal logic)
from models import Category, Submission, SubmissionAnswer, Evaluation, EvaluationAnswer, Question

# Environment and utilities
from dotenv import load_dotenv
load_dotenv()

MAX_SCORE = float(os.getenv("MAX_SCORE"))
AGREE_SCORE = float(os.getenv("AGREE_SCORE"))
DISAGREE_SCORE = float(os.getenv("DISAGREE_SCORE"))
NEITHER_SCORE = float(os.getenv("NEITHER_SCORE"))

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown events"""
    print("Starting up application with MongoDB...")

    print("Application started successfully!")
    
    yield  # Application runs here
    
    # Shutdown code
    close_database_connection()
    print("Shutting down application...")

app = FastAPI(title="Submission Evaluation API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Category Endpoints
@app.post("/category", response_model=CategoryRead)
def create_category(category: CategoryCreate):
    db = get_db()
    categories_collection = get_categories_collection()
    
    # Check if category with this slug already exists
    existing_category = categories_collection.find_one({"slug": category.slug})
    if existing_category:
        raise HTTPException(
            status_code=400, 
            detail=f"Category with slug '{category.slug}' already exists"
        )
    
    # Create new category
    category_dict = category.model_dump()
    result = categories_collection.insert_one(category_dict)
    
    # Return created category
    created_category = categories_collection.find_one({"_id": result.inserted_id})
    # Remove MongoDB _id field to avoid conflicts
    created_category.pop('_id', None)
    return CategoryRead(**created_category)

@app.get("/categories", response_model=List[CategoryRead])
def get_categories():
    db = get_db()
    categories_collection = get_categories_collection()
    
    categories = []
    cursor = categories_collection.find()
    for category in cursor:
        category.pop('_id', None)
        categories.append(CategoryRead(**category))
    
    return categories

@app.get("/categories/{slug}", response_model=CategoryReadWithSubmissions)
def get_category_by_slug(slug: str):
    db = get_db()
    categories_collection = get_categories_collection()
    submissions_collection = get_submissions_collection()
    evaluations_collection = get_evaluations_collection()
    
    category = categories_collection.find_one({"slug": slug})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    submissions_cursor = submissions_collection.find({"category.slug": slug})
    submissions = []

    for submission in submissions_cursor:
        submission_id = str(submission["id"])
                            
        # Get evaluation stats
        evaluations = list(evaluations_collection.find(
            {"submission_id": submission_id}
        ).sort("date_completed", -1))

        last_evaluation_date = evaluations[0]["date_completed"] if evaluations else None
        evaluation_count = len(evaluations)

        submission_read = SubmissionRead(
            id=submission_id,
            project_id=submission["project_id"],
            project_name=submission["project_name"],
            karma_gap_id=submission["karma_gap_id"],
            date_completed=submission.get("date_completed"),
            score=submission.get("score"),
            category=category,
            last_evaluation_date=last_evaluation_date,
            evaluation_count=evaluation_count
        )
        submissions.append(submission_read)

    return CategoryReadWithSubmissions(**category, submissions=submissions)

# Question Endpoints
@app.get("/questions", response_model=List[QuestionRead])
def get_questions():
    db = get_db()
    questions_collection = get_questions_collection()
    
    questions = []
    cursor = questions_collection.find()
    for question in cursor:
        question.pop('_id', None)
        questions.append(QuestionRead(**question))
    
    return questions

# @app.post("/questions", response_model=QuestionRead)
# def create_question(question: QuestionCreate):
#     db = get_db()
#     questions_collection = get_questions_collection()
    
#     # Create new question
#     question_dict = question.model_dump()
#     question_dict['_id'] = str(uuid.uuid4())
#     result = questions_collection.insert_one(question_dict)
    
#     # Return created question
#     created_question = questions_collection.find_one({"_id": result.inserted_id})
#     created_question.pop('_id', None)
#     return QuestionRead(**created_question)

# Submission Endpoints
@app.post("/submission", response_model=SubmissionWithAnswersRead)
def create_submission_with_answers(submission_data: SubmissionCreate):
    db = get_db()
    submissions_collection = get_submissions_collection()
    categories_collection = get_categories_collection()
    questions_collection = get_questions_collection()
    
    # Verify category exists
    category = categories_collection.find_one({"slug": submission_data.category})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get questions for answers
    question_ids = [answer.question_id for answer in submission_data.answers]
    questions_cursor = questions_collection.find({"_id": {"$in": question_ids}})
    questions_dict = {}
    for question in questions_cursor:
        questions_dict[question["_id"]] = question
    
    # Create answers
    created_answers = []
    for answer_data in submission_data.answers:
        answer = SubmissionAnswer(
            id=str(uuid.uuid4()),
            question_id=answer_data.question_id,
            answer=answer_data.answer
        )
        created_answers.append(answer)
    
    # Create submission
    submission = Submission(
        id=str(uuid.uuid4()),
        date_completed=datetime.now(timezone.utc),
        project_id=submission_data.project_id,
        project_name=submission_data.project_name,
        karma_gap_id=submission_data.karma_gap_id,
        score=None,
        answers=created_answers,
        evaluations=[],
        category=Category(**category)
    )
    
    # Insert submission
    submission_dict = submission.model_dump()
    # Convert embedded objects to dictionaries for MongoDB storage
    submission_dict['answers'] = [answer.model_dump() for answer in submission.answers]
    submission_dict['category'] = category
    result = submissions_collection.insert_one(submission_dict)
    
    # Return created submission
    created_submission = submissions_collection.find_one({"_id": result.inserted_id})

    last_evaluation_date = None
    evaluation_count = 0

    # Convert back to proper model format
    answers_with_questions = []
    for answer_dict in created_submission['answers']:
        question = questions_dict.get(answer_dict['question_id'])
        
        if question:
            answer_read = SubmissionAnswerRead(
                id=answer_dict['id'],
                question_id=answer_dict['question_id'],
                answer=answer_dict['answer'],
                question=Question(**question)
            )
            answers_with_questions.append(answer_read)
    
    return SubmissionWithAnswersRead(
        id=created_submission['id'],
        date_completed=created_submission['date_completed'],
        project_id=created_submission['project_id'],
        project_name=created_submission['project_name'],
        karma_gap_id=created_submission['karma_gap_id'],
        score=created_submission['score'],
        answers=answers_with_questions,
        category=Category(**created_submission['category']),
        last_evaluation_date=last_evaluation_date,
        evaluation_count=evaluation_count
    )

@app.get("/submissions/{submission_id}", response_model=SubmissionWithAnswersRead)
async def get_submission(submission_id: str):
    db = get_db()
    submissions_collection = get_submissions_collection()
    questions_collection = get_questions_collection()
    categories_collection = get_categories_collection()
    evaluations_collection = get_evaluations_collection()
    
    # Get submission
    submission = submissions_collection.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Get category
    category = categories_collection.find_one({"slug": submission['category']['slug']})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get evaluation stats
    evaluations = list(evaluations_collection.find(
        {"submission_id": submission_id}
    ).sort("date_completed", -1))

    last_evaluation_date = evaluations[0]["date_completed"] if evaluations else None
    evaluation_count = len(evaluations)
    
    # Get questions for answers
    if 'answers' in submission:
        question_ids = [answer['question_id'] for answer in submission['answers']]
        questions_cursor = questions_collection.find({"id": {"$in": question_ids}})
        questions_dict = {}
        for question in questions_cursor:
            questions_dict[question["id"]] = question
        
        # Convert answers with questions
        answers_with_questions = []
        for answer_dict in submission['answers']:
            question = questions_dict.get(answer_dict['question_id'])
            if question:
                answer_read = SubmissionAnswerRead(
                    id=answer_dict['id'],
                    question_id=answer_dict['question_id'],
                    answer=answer_dict['answer'],
                    question=Question(**question)
                )
                answers_with_questions.append(answer_read)
    else:
        answers_with_questions = []

     # Get Karma GAP data
    karma_data = None
    try:
        karma_data = await utils.get_karma_data(submission['karma_gap_id'])
    except Exception as e:
        print(f"Warning: Could not fetch Karma GAP data: {e}")
    
    submission.pop('_id', None)
    return SubmissionWithAnswersRead(
        id=submission['id'],
        date_completed=submission.get('date_completed'),
        project_id=submission['project_id'],
        project_name=submission["project_name"],
        karma_gap_id=submission['karma_gap_id'],
        score=submission.get('score', 0.0),
        answers=answers_with_questions,
        category=Category(**category),
        karma_data=karma_data,
        last_evaluation_date=last_evaluation_date,
        evaluation_count=evaluation_count
    )

# @app.get("/submissions", response_model=List[SubmissionWithAnswersRead])
# def get_submissions():
#     db = get_db()
#     submissions_collection = get_submissions_collection()
    
#     submissions = []
#     cursor = submissions_collection.find()
#     for submission in cursor:
#         submission.pop('_id', None)
#         # Convert embedded objects properly
#         if 'answers' in submission:
#             submission['answers'] = [SubmissionAnswerRead(**answer) for answer in submission['answers']]
#         if 'category' in submission and submission['category']:
#             submission['category'] = CategoryRead(**submission['category'])
#         submissions.append(SubmissionWithAnswersRead(**submission))
    
#     return submissions

# Evaluation Endpoints
@app.post("/evaluation", response_model=EvaluationWithAnswersRead)
def create_evaluation_with_answers(evaluation_data: EvaluationCreate):
    db = get_db()
    submissions_collection = get_submissions_collection()
    evaluations_collection = get_evaluations_collection()
    questions_collection = get_questions_collection()
    
    # Verify submission exists
    submission = submissions_collection.find_one({"id": evaluation_data.submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    evaluation_score = 0
    # Calculate evaluation score from answer scores
    for answer in evaluation_data.answers:
        if answer.answer == "1":
            evaluation_score += AGREE_SCORE
        elif answer.answer == "2":
            evaluation_score += DISAGREE_SCORE
        elif answer.answer == "3":
            evaluation_score += NEITHER_SCORE
        else:
            evaluation_score = 0.0

    calculated_score = round(evaluation_score / MAX_SCORE, 4)  # Normalize to 0-1 range
    
    # Create evaluation answers
    created_answers = []
    for answer_data in evaluation_data.answers:
        answer = EvaluationAnswer(
            id=str(uuid.uuid4()),
            question_id=answer_data.question_id,
            answer=answer_data.answer,
        )
        created_answers.append(answer)
    
    # Create evaluation
    evaluation = Evaluation(
        id=str(uuid.uuid4()),
        date_completed=datetime.now(timezone.utc),
        evaluator=evaluation_data.evaluator,
        submission_id=evaluation_data.submission_id,
        score=calculated_score,
        answers=created_answers
    )
    
    # Add evaluation to submission
    submission_evaluations = submission.get('evaluations', [])
    submission_evaluations.append(evaluation.model_dump())

    # Calculate new submission score (average of all evaluation scores)
    all_evaluation_scores = []
    for existing_eval in submission_evaluations:
        if isinstance(existing_eval, dict) and existing_eval.get('score') is not None:
            all_evaluation_scores.append(existing_eval['score'])
        elif hasattr(existing_eval, 'score') and existing_eval.score is not None:
            all_evaluation_scores.append(existing_eval.score)
    
    new_submission_score = 0.0
    if all_evaluation_scores:
        new_submission_score = round(sum(all_evaluation_scores) / len(all_evaluation_scores), 4)
    
    # Update submission with new evaluation
    submissions_collection.update_one(
        {"id": evaluation_data.submission_id},
        {
            "$set": {
                "evaluations": submission_evaluations,
                "score": new_submission_score
            }
        }
    )
    
    # Also store evaluation separately
    evaluation_dict = evaluation.model_dump()
    evaluation_dict['answers'] = [answer.model_dump() for answer in evaluation.answers]
    evaluations_collection.insert_one(evaluation_dict)
    
    # Get questions for answers
    question_ids = [answer.question_id for answer in evaluation.answers]
    questions_cursor = questions_collection.find({"id": {"$in": question_ids}})
    questions_dict = {}
    for question in questions_cursor:
        questions_dict[question["id"]] = question
    
    # Convert answers with questions for response
    answers_with_questions = []
    for answer in evaluation.answers:
        question = questions_dict.get(answer.question_id)
        if question:
            answer_read = EvaluationAnswerRead(
                id=answer.id,
                question_id=answer.question_id,
                answer=answer.answer,
                question=Question(**question)
            )
            answers_with_questions.append(answer_read)
    
    return EvaluationWithAnswersRead(
        id=evaluation.id,
        date_completed=evaluation.date_completed,
        evaluator=evaluation.evaluator,
        submission_id=evaluation.submission_id,
        score=evaluation.score,
        answers=answers_with_questions
    )

@app.get("/evaluations/{evaluation_id}", response_model=EvaluationWithAnswersRead)
def get_evaluation(evaluation_id: str):
    db = get_db()
    evaluations_collection = get_evaluations_collection()
    questions_collection = get_questions_collection()
    
    evaluation = evaluations_collection.find_one({"id": evaluation_id})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Get questions for answers
    if 'answers' in evaluation:
        question_ids = [answer['question_id'] for answer in evaluation['answers']]
        questions_cursor = questions_collection.find({"id": {"$in": question_ids}})
        questions_dict = {}
        for question in questions_cursor:
            questions_dict[question["id"]] = question
        
        # Convert answers with questions
        answers_with_questions = []
        for answer_dict in evaluation['answers']:
            question = questions_dict.get(answer_dict['question_id'])
            if question:
                answer_read = EvaluationAnswerRead(
                    id=answer_dict['id'],
                    question_id=answer_dict['question_id'],
                    answer=answer_dict['answer'],
                    question=Question(**question)
                )
                answers_with_questions.append(answer_read)
    else:
        answers_with_questions = []
    
    evaluation.pop('_id', None)
    return EvaluationWithAnswersRead(
        id=evaluation['id'],
        date_completed=evaluation.get('date_completed'),
        evaluator=evaluation['evaluator'],
        submission_id=evaluation['submission_id'],
        score=evaluation.get('score'),
        answers=answers_with_questions
    )

@app.get("/submissions/{submission_id}/evaluations", response_model=List[EvaluationWithAnswersRead])
def get_evaluations_by_submission(submission_id: str):
    db = get_db()
    submissions_collection = get_submissions_collection()
    questions_collection = get_questions_collection()
    
    # Verify submission exists
    submission = submissions_collection.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Get evaluations from submission
    evaluations_data = submission.get('evaluations', [])
    
    # Process each evaluation
    result = []
    for eval_data in evaluations_data:
        # Get questions for answers
        if 'answers' in eval_data:
            question_ids = [answer['question_id'] for answer in eval_data['answers']]
            questions_cursor = questions_collection.find({"id": {"$in": question_ids}})
            questions_dict = {}
            for question in questions_cursor:
                questions_dict[question["id"]] = question
            
            # Convert answers with questions
            answers_with_questions = []
            for answer_dict in eval_data['answers']:
                question = questions_dict.get(answer_dict['question_id'])
                if question:
                    answer_read = EvaluationAnswerRead(
                        id=answer_dict['id'],
                        question_id=answer_dict['question_id'],
                        answer=answer_dict['answer'],
                        score=answer_dict.get('score'),
                        question=Question(**question)
                    )
                    answers_with_questions.append(answer_read)
        else:
            answers_with_questions = []
        
        # Create evaluation response
        evaluation_read = EvaluationWithAnswersRead(
            id=eval_data['id'],
            date_completed=eval_data.get('date_completed'),
            evaluator=eval_data['evaluator'],
            submission_id=eval_data['submission_id'],
            score=eval_data.get('score'),
            answers=answers_with_questions
        )
        result.append(evaluation_read)
    
    return result
