import os
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware 
from app.routers import application
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel 
from app.db.session import engine

DATABASE_URL = str(os.getenv("DATABASE_URL", "sqlite:///todo.db"))
SECRET_KEY = str(os.getenv('SECRET_KEY', 'K%!MaoL26XQe8iGAAyDrmbkw&bqE$hCPw4hSk!Hf'))
REGION = str(os.getenv('REGION'))
USER_POOL_ID = str(os.getenv('USER_POOL_ID'))
CLIENT_ID = str(os.getenv('CLIENT_ID'))
FRONTEND_URL = str(os.getenv('FRONTEND_URL'))

# AWS Cognito configuration
COGNITO_KEYS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": True}, lifespan=lifespan)

origins = [
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(application.router, prefix="/applications", tags=["applications"])

APPLICATION_FILES_DIR = os.getenv("APPLICATION_FILES_DIR", "application_files")
os.makedirs(APPLICATION_FILES_DIR, exist_ok=True)

app.mount("/application_files", StaticFiles(directory=APPLICATION_FILES_DIR), name="application_files")
