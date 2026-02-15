from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# --- Enums ---

class SummaryType(str, Enum):
    PAGE = "page"
    COMPLETE = "complete"
    CHAPTER = "chapter"


class QuizType(str, Enum):
    COMPLETE = "complete"
    CHAPTER = "chapter"


# --- Request Models ---

class AskRequest(BaseModel):
    pdf: str
    question: str


class SummaryRequest(BaseModel):
    pdf: str
    type: SummaryType
    page_number: Optional[int] = None
    chapter: Optional[str] = None


class QuizRequest(BaseModel):
    pdf: str
    type: QuizType
    chapter: Optional[str] = None
    num_questions: Optional[int] = 10


# --- Response Models ---

class UploadResponse(BaseModel):
    message: str
    name: str
    pages: int
    chapters_found: List[str]


class PDFInfo(BaseModel):
    name: str
    uploaded_by: str
    total_pages: int
    chapters: List[str]
    upload_date: str


class AskResponse(BaseModel):
    answer: str
    context_found: bool
    pdf: str


class SummaryResponse(BaseModel):
    pdf: str
    type: str
    summary: str
    scope: Optional[str] = None  # e.g. "Page 3" or "Chapter 1"


class QuizQuestion(BaseModel):
    type: str  # "mcq", "true_false", "short_answer"
    question: str
    options: Optional[List[str]] = None  # for MCQ
    answer: str
    explanation: str


class QuizResponse(BaseModel):
    pdf: str
    type: str
    questions: List[QuizQuestion]
