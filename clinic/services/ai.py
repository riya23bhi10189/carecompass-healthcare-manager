import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def create_pre_visit_summary(symptoms):
    fallback = {
        "urgency": "MEDIUM",
        "chief_complaint": symptoms[:160],
        "suggested_questions": [
            "When did these symptoms begin?",
            "Have the symptoms changed over time?",
            "Are there allergies or current medicines to consider?"
        ],
        "source": "FALLBACK"
    }

    # The application must still book appointments if the LLM is unavailable.
    if not client:
        return fallback

    prompt = f"""
You are a healthcare intake assistant. Do not diagnose.

Analyse these symptoms and return JSON only in this exact format:
{{
  "urgency": "LOW, MEDIUM, or HIGH",
  "chief_complaint": "short summary",
  "suggested_questions": [
    "question one",
    "question two",
    "question three"
  ]
}}

Symptoms: {symptoms}
"""

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
            store=False
        )

        result = json.loads(response.output_text)
        result["source"] = "LLM"
        return result

    except Exception as error:
        print("AI summary fallback used:", error)
        return fallback


def create_post_visit_summary(notes, prescription):
    fallback = {
        "summary": notes,
        "medication_schedule": prescription or "Follow your doctor's instructions.",
        "follow_up": "Contact the clinic if symptoms worsen.",
        "source": "FALLBACK"
    }

    if not client:
        return fallback

    prompt = f"""
Convert the following clinical notes into clear, patient-friendly JSON.
Do not add diagnoses or advice that is not in the doctor's notes.

Return exactly:
{{
  "summary": "simple explanation",
  "medication_schedule": "clear prescription instructions",
  "follow_up": "next steps"
}}

Clinical notes: {notes}
Prescription: {prescription}
"""

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
            store=False
        )

        result = json.loads(response.output_text)
        result["source"] = "LLM"
        return result

    except Exception as error:
        print("AI post-visit fallback used:", error)
        return fallback