from fastapi import FastAPI
from app.routes import auth

app = FastAPI(title="Skillify API")

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
