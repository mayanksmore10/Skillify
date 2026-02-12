import re
import uuid

# TEMP IN-MEMORY STORE (replace with DB later)
USERS_DB = {}

def extract_email(text: str):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group() if match else None

def create_or_get_user(resume_text: str, skills: list):
    email = extract_email(resume_text)

    if not email:
        email = f"user_{uuid.uuid4()}@skillify.ai"

    if email in USERS_DB:
        return USERS_DB[email]

    user = {
        "user_id": str(uuid.uuid4()),
        "email": email,
        "skills": skills
    }

    USERS_DB[email] = user
    return user
