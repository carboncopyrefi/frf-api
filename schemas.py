from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Base configuration
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

class KarmaData(BaseModel):
    project_details: dict
    updates: List[dict]

# Question Schemas
class QuestionBase(BaseSchema):
    project_statement: str
    project_description: Optional[str] = None
    evaluator_statement: str
    evaluator_description: Optional[str] = None
    section: str
    order: int

class QuestionCreate(QuestionBase):
    pass

class QuestionRead(QuestionBase):
    id: str

# Category Schemas
class CategoryBase(BaseSchema):
    name: str
    description: Optional[str] = None
    slug: str

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    _id: str

class CategoryReadWithSubmissions(CategoryRead):
    submissions: List["SubmissionRead"] = []

# Submission Schemas
class SubmissionBase(BaseSchema):
    project_id: str
    project_name: str
    karma_gap_id: str

class SubmissionAnswerCreate(BaseSchema):
    question_id: str
    answer: str

class SubmissionCreate(SubmissionBase):
    answers: List[SubmissionAnswerCreate]
    category: str

class SubmissionRead(SubmissionBase):
    id: str
    date_completed: Optional[datetime] = None
    score: Optional[float] | None
    category: CategoryRead
    last_evaluation_date: Optional[datetime] | None
    evaluation_count: int | None

class SubmissionAnswerRead(BaseSchema):
    id: str
    question_id: str
    answer: str
    question: QuestionRead

class SubmissionWithAnswersRead(SubmissionRead):
    answers: List[SubmissionAnswerRead]
    category: CategoryRead
    karma_data: Optional[KarmaData] = None

# Evaluation Schemas
class EvaluationBase(BaseSchema):
    evaluator: str
    submission_id: str

class EvaluationAnswerCreate(BaseSchema):
    question_id: str
    answer: str

class EvaluationCreate(EvaluationBase):
    answers: List[EvaluationAnswerCreate]

class EvaluationRead(EvaluationBase):
    id: str
    date_completed: Optional[datetime] = None
    score: Optional[float] = None

class EvaluationAnswerRead(BaseSchema):
    id: str
    question_id: str
    answer: str
    question: QuestionRead

class EvaluationWithAnswersRead(EvaluationRead):
    answers: List[EvaluationAnswerRead]

# Update forward references
CategoryReadWithSubmissions.model_rebuild()
