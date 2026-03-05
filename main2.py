from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
import schemas
from sqlalchemy.orm import Session
import models
from database import engine, SessionLocal
from fastapi import Form, Depends, UploadFile, File
from fastapi.responses import RedirectResponse
import shutil
import os
from utils import hash_password,verify_password
from starlette.middleware.sessions import SessionMiddleware 
import httpx
import asyncio

ADZUNA_APP_ID = "42f1cf26"
ADZUNA_KEY = "72d57e1bd33c449d57d52046a03d34f7"
ADZUNA_COUNTRY = "in" # Try 'us', 'gb', or 'in' depending on where you want the data from

# A robust list of skills matching your frontend categories
SKILLS_TO_TRACK = [
    "React", "Python", "TypeScript", "AWS", "Docker","javascript","AI","ML","Data Science","Azure","GCP","lambda","mongodb","google cloud"
    "Kubernetes", "TensorFlow", "Node.js", "Go", "Rust", "SQL", "Figma","Java","C++","C","Linux","Bash"
]
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="some-random-secret-string")
models.Base.metadata.create_all(bind=engine)


def get_db(): 
    db = SessionLocal() 
    try: 
        yield db
    finally:
        db.close()
print("STATIC PATH =", os.path.abspath("static"))

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse("landing-page.html", {"request": request})

@app.get("/register")
def register(request: Request):
    return templates.TemplateResponse('register.html',{"request":request})

@app.post("/register")
def register_user(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    existing_user = db.query(models.User).filter(models.User.email == email).first()

    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email already registered"
        })

    hashed_pw = hash_password(password)

    user = models.User(
        fullname=fullname,
        email=email,
        hashed_password=hashed_pw
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse("/login", status_code=303)

@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse('login.html',{"request":request})

@app.post('/login')
def login_user(
    request:Request,
    email:str = Form(...),
    password:str = Form(...),
    db:Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "User not found"
        })

    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid password"
        })
    request.session['user_id'] = user.id
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/profile")
def profile(request: Request, db: Session = Depends(get_db)):
    

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse("/login")


    user = db.query(models.User).filter(models.User.id == user_id).first()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

@app.get("/logout")
def logout(requets:Request):
    return RedirectResponse("/login",status_code=303)

@app.get("/upload-resume")
def upload_resume_page(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("upload_resume.html", {"request": request})

@app.post("/upload-resume")
async def upload_resume(
    request: Request,
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        return RedirectResponse("/login", status_code=303)


    upload_dir = os.path.join("static", "resumes")
    os.makedirs(upload_dir, exist_ok=True)


    filename = f"{user_id}_{resume.filename}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)


    user.resume_filename = filename
    db.commit()
    db.refresh(user)

    return RedirectResponse("/profile", status_code=303)


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/market-data")
async def get_market_data():
    results = []

    # Validation
    if not ADZUNA_APP_ID or not ADZUNA_KEY:
        print("❌ ERROR: API Keys are missing in main.py")
        return [] 

    async with httpx.AsyncClient() as client:
        tasks = []
        for skill in SKILLS_TO_TRACK:
            url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_KEY,
                "what": skill,
                "content-type": "application/json"
            }
            tasks.append(client.get(url, params=params))
        
        try:
            responses = await asyncio.gather(*tasks)

            for skill, response in zip(SKILLS_TO_TRACK, responses):
                if response.status_code == 200:
                    data = response.json()
                    job_count = data.get('count', 0)
                    
                    # --- IMPROVED SALARY LOGIC ---
                    total_salary = 0
                    salary_samples = 0
                    
                    # 1. Check if the root has a 'mean' value (Adzuna sometimes provides this)
                    if 'mean' in data:
                        avg_salary = data['mean']
                    else:
                        # 2. If not, calculate from individual job results
                        for job in data.get('results', []):
                            # Case A: Min and Max both exist -> Take average
                            if 'salary_min' in job and 'salary_max' in job:
                                total_salary += (job['salary_min'] + job['salary_max']) / 2
                                salary_samples += 1
                            # Case B: Only Min exists
                            elif 'salary_min' in job:
                                total_salary += job['salary_min']
                                salary_samples += 1
                            # Case C: Only Max exists
                            elif 'salary_max' in job:
                                total_salary += job['salary_max']
                                salary_samples += 1
                        
                        avg_salary = (total_salary / salary_samples) if salary_samples > 0 else 0
                    
                    results.append({
                        "name": skill,
                        "jobs": job_count,
                        "salary": avg_salary
                    })
                else:
                    results.append({"name": skill, "jobs": 0, "salary": 0})
        
        except Exception as e:
            print(f"❌ Critical Connection Error: {e}")
            return []

    return results