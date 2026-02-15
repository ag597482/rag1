import json
import re
from typing import List, Dict, Optional
from openai import OpenAI
from app.core.config import settings
from app.services.retrieval_service import get_content_by_chapter, get_all_content

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _generate_quiz_from_llm(
    content: str, scope_description: str, num_questions: int = 10
) -> List[Dict]:
    """Use the LLM to generate a mixed quiz from the provided content."""
    if not content or not content.strip():
        return []

    # Truncate very long content
    max_content_length = 80000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated...]"

    prompt = f"""You are an expert quiz generator for educational content. Generate a quiz based on the following content to test the reader's understanding.

Scope: {scope_description}
Number of questions: {num_questions}

Requirements:
- Generate a MIX of question types:
  - Multiple Choice Questions (MCQ) with exactly 4 options (A, B, C, D)
  - True/False questions
  - Short Answer questions
- Roughly distribute: 50% MCQ, 25% True/False, 25% Short Answer
- Questions should test comprehension, not just recall
- Each question must have a clear correct answer and a brief explanation
- Cover different parts/topics of the content

Return the quiz as a JSON array with this exact format:
[
  {{
    "type": "mcq",
    "question": "What is ...?",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "answer": "A) Option 1",
    "explanation": "This is correct because..."
  }},
  {{
    "type": "true_false",
    "question": "Statement to evaluate as true or false.",
    "options": ["True", "False"],
    "answer": "True",
    "explanation": "This is true because..."
  }},
  {{
    "type": "short_answer",
    "question": "Explain briefly...",
    "options": null,
    "answer": "Expected answer summary",
    "explanation": "The key points are..."
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text.

Content:
{content}"""

    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = response.choices[0].message.content

    # Parse the JSON response
    try:
        # Try to extract JSON from the response (handle markdown code blocks)
        json_match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
        else:
            questions = json.loads(raw_response)
    except json.JSONDecodeError:
        print(f"⚠️ Failed to parse quiz JSON, attempting cleanup...")
        # Try to clean up common issues
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            questions = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            print(f"❌ Could not parse quiz response")
            return []

    # Validate and normalize the questions
    validated = []
    for q in questions:
        validated.append({
            "type": q.get("type", "mcq"),
            "question": q.get("question", ""),
            "options": q.get("options"),
            "answer": q.get("answer", ""),
            "explanation": q.get("explanation", ""),
        })

    return validated


def generate_complete_quiz(
    pdf_name: str, num_questions: int = 10
) -> List[Dict]:
    """Generate a quiz covering the entire PDF."""
    content = get_all_content(pdf_name)
    return _generate_quiz_from_llm(
        content,
        f"Complete book/document '{pdf_name}'",
        num_questions,
    )


def generate_chapter_quiz(
    pdf_name: str, chapter: str, num_questions: int = 10
) -> List[Dict]:
    """Generate a quiz for a specific chapter/unit of a PDF."""
    content = get_content_by_chapter(pdf_name, chapter)
    return _generate_quiz_from_llm(
        content,
        f"Chapter/Unit '{chapter}' of '{pdf_name}'",
        num_questions,
    )
