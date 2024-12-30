import json
import boto3
import os
import logging
from fastapi import FastAPI, BackgroundTasks
from starlette.middleware.sessions import SessionMiddleware 
from app.routers import application
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel 
from app.db.session import engine
from app.core.config import settings
from apscheduler.schedulers.background import BackgroundScheduler
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    SQLModel.metadata.create_all(engine)
    yield

QUEUE_URL = str(os.getenv("QUEUE_URL"))
AWS_ACESS_KEY_ID = str(os.getenv("AWS_ACCESS_KEY_ID"))
AWS_SECRET_ACCESS_KEY = str(os.getenv("AWS_SECRET_ACCESS_KEY"))
REGION = str(os.getenv("REGION"))

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": True}, lifespan=lifespan)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(application.router, prefix="/applications", tags=["applications"])

APPLICATION_FILES_DIR = os.getenv("APPLICATION_FILES_DIR", "application_files")
os.makedirs(APPLICATION_FILES_DIR, exist_ok=True)

app.mount("/application_files", StaticFiles(directory=APPLICATION_FILES_DIR), name="application_files")

sqs = boto3.client(
    'sqs',
    aws_access_key_id=AWS_ACESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
def process_message(message):
    # Add your message processing logic here
    body = json.loads(message['Body'])

def receive_message():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5,
    )
    messages = response.get('Messages', [])
    for message in messages:
        body = json.loads(message['Body'])
        logging.info(f"Received message: {body}")
        process_message(message)
        # Delete the message from the queue

scheduler = BackgroundScheduler()
scheduler.add_job(receive_message, 'interval', seconds=2, max_instances=10)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
scheduler.start()