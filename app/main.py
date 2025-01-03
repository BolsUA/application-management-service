import os
from fastapi import FastAPI
from app.routers import application
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, select
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": True}, lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(application.router, prefix="/applications", tags=["applications"])

APPLICATION_FILES_DIR = os.getenv("APPLICATION_FILES_DIR", "application_files")
os.makedirs(APPLICATION_FILES_DIR, exist_ok=True)

app.mount("/application_files", StaticFiles(directory=APPLICATION_FILES_DIR), name="application_files")
