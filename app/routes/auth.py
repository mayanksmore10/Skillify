from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from app.services.resume_parser import extract_text_from_resume
from app.services.skill_extractor import extract_skills
from app.services.user_service import create_or_get_user
from app.core.security import create_access_token

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = f"{UPLOAD_DIR}/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Step 1: Extract text
    resume_text = extract_text_from_resume(file_path)

    # Step 2: Extract skills
    skills = extract_skills(resume_text)

    # Step 3: Create or fetch user
    user = create_or_get_user(resume_text, skills)

    # Step 4: Generate JWT
    token = create_access_token({"user_id": user["user_id"]})

    # Step 5: Clean up
    os.remove(file_path)

    return {
        "message": "Account created successfully",
        "user_id": user["user_id"],
        "skills": skills,
        "access_token": token
    }
