from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_answer(question: str, context: str):
    prompt = f"""
    You are a helpful assistant.
    Answer ONLY using the provided context.
    If the answer cannot be determined from the context, say "I couldn't find that specific information in the documents."

    Context:
    {context}

    Question:
    {question}

    Answer:
    """

    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        temperature=settings.TEMPERATURE,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
