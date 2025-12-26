from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

# Base configuration
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# Category Models
class CategoryBase(BaseSchema):
    name: str
    description: Optional[str] = None
    slug: str
    evaluators: List[str]

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class Category(CategoryBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# Question Models
class QuestionBase(BaseSchema):
    project_statement: str
    project_description: Optional[str] = None
    evaluator_statement: str
    evaluator_description: Optional[str] = None
    section: str
    order: int

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(QuestionBase):
    pass

class Question(QuestionBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# Answer Models
class SubmissionAnswerBase(BaseSchema):
    question_id: str
    answer: str = Field(..., max_length=1800)

class SubmissionAnswerCreate(SubmissionAnswerBase):
    pass

class SubmissionAnswerUpdate(SubmissionAnswerBase):
    pass

class SubmissionAnswer(SubmissionAnswerBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class EvaluationAnswerBase(BaseSchema):
    question_id: str
    answer: str

class EvaluationAnswerCreate(EvaluationAnswerBase):
    pass

class EvaluationAnswerUpdate(EvaluationAnswerBase):
    pass

class EvaluationAnswer(EvaluationAnswerBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# Submission Models
class SubmissionBase(BaseSchema):
    project_id: str
    project_name: str
    karma_gap_id: str
    category: str

class EvaluationCreateForSubmission(BaseSchema):
    evaluator: str
    answers: List[EvaluationAnswerCreate]

class SubmissionCreate(SubmissionBase):
    answers: List[SubmissionAnswerCreate]
    owner: str

class SubmissionUpdate(SubmissionBase):
    pass

class SubmissionInDBBase(SubmissionBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date_completed: Optional[datetime] = None
    score: float | None

class Submission(SubmissionInDBBase):
    answers: List[SubmissionAnswer] = []
    evaluations: List["Evaluation"] = []
    category: Category
    owner: str

    class Config:
        from_attributes = True

# Evaluation Models
class EvaluationBase(BaseSchema):
    evaluator: str
    submission_id: str

class EvaluationCreate(EvaluationBase):
    answers: List[EvaluationAnswerCreate]

class EvaluationUpdate(EvaluationBase):
    pass

class EvaluationInDBBase(EvaluationBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date_completed: Optional[datetime] = None
    score: Optional[float] = None

class Evaluation(EvaluationInDBBase):
    answers: List[EvaluationAnswer] = []

    class Config:
        from_attributes = True

# Update forward references
Submission.model_rebuild()
Evaluation.model_rebuild()
