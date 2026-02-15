from openai import OpenAI
from app.core.config import settings
from app.services.retrieval_service import (
    get_content_by_page,
    get_content_by_chapter,
    get_all_content,
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _generate_summary_from_llm(content: str, scope_description: str) -> str:
    """Use the LLM to generate a summary of the provided content."""
    if not content or not content.strip():
        return f"No content found for {scope_description}."

    # For very long content, truncate to fit within context window
    max_content_length = 80000  # conservative limit
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n\n[Content truncated...]"

    prompt = f"""You are an expert book summarizer. Generate a clear, comprehensive, and well-structured summary of the following content.

Scope: {scope_description}

Instructions:
- Provide a concise yet thorough summary capturing all key points, themes, and important details.
- Use clear headings and bullet points where appropriate.
- Highlight any key terms, concepts, or arguments.
- Maintain the logical flow of the original content.

Content:
{content}

Summary:"""

    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_page_summary(pdf_name: str, page_number: int) -> str:
    """Generate a summary for a specific page of a PDF."""
    content = get_content_by_page(pdf_name, page_number)
    return _generate_summary_from_llm(
        content, f"Page {page_number} of '{pdf_name}'"
    )


def generate_complete_summary(pdf_name: str) -> str:
    """Generate a complete summary of the entire PDF."""
    content = get_all_content(pdf_name)
    return _generate_summary_from_llm(
        content, f"Complete book/document '{pdf_name}'"
    )


def generate_chapter_summary(pdf_name: str, chapter: str) -> str:
    """Generate a summary for a specific chapter/unit of a PDF."""
    content = get_content_by_chapter(pdf_name, chapter)
    return _generate_summary_from_llm(
        content, f"Chapter/Unit '{chapter}' of '{pdf_name}'"
    )
