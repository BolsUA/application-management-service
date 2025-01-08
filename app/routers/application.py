from typing import List, Dict, Annotated
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import get_db
from app.schemas import schemas
from app.crud import crud_application
from app.core.config import settings
import jwt
from jwt import PyJWKClient
import os
import boto3
import json
import logging

router = APIRouter()

oauth2_scheme = HTTPBearer()

DEADLINE_QUEUE_URL = str(os.getenv("DEADLINE_QUEUE_URL"))
TO_GRADING_QUEUE_URL = str(os.getenv("TO_GRADING_QUEUE_URL"))
AWS_ACESS_KEY_ID = str(os.getenv("AWS_ACCESS_KEY_ID"))
AWS_SECRET_ACCESS_KEY = str(os.getenv("AWS_SECRET_ACCESS_KEY"))
REGION = str(os.getenv("REGION"))

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    try:
        # Fetch public keys from AWS Cognito
        jwks_client = PyJWKClient(settings.COGNITO_KEYS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate the token
        payload = jwt.decode(token, signing_key.key, algorithms=["RS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

TokenDep = Annotated[Dict, Depends(verify_token)]

@router.get("/health")
def health_check():
    return {"status": "ok"}

# applications variable cant be a schemas because of the argument document_file...
@router.post("/", response_model=schemas.ApplicationBase)
def create_application(
        _: TokenDep,
        db: Session = Depends(get_db),
        scholarship_id: int = Form(...),
        user_id: str = Form(...),
        status: schemas.ApplicationStatus = Form(schemas.ApplicationStatus.submitted),
        name: str = Form(...),
        document_file: List[UploadFile] = File(None),
    ):
    
    application = schemas.ApplicationBase(
        id=0, # probably not the best way to handle this.....
        scholarship_id=scholarship_id,
        user_id=user_id,
        status=status,
        # created_at is default
        name=name,
        # Handle documents separately
    )

    # Create the application record
    db_application = crud_application.create_application(db, application)

    # Create the document records
    for document in  enumerate(document_file or []):
        crud_application.create_application_document(db, db_application.id, document[1])

    return db_application

@router.get("/", response_model=list[schemas.ApplicationBase])
def get_applications(_: TokenDep, user_id: str, db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return crud_application.get_applications(db, user_id, skip, limit)

@router.get("/{application_id}/details", response_model=schemas.ApplicationBase)
def get_application(_: TokenDep, application_id: int, db: Session = Depends(get_db)):
    return crud_application.get_application(db, application_id)

@router.put("/{application_id}/status", response_model=schemas.ApplicationBase)
def update_application_status(_: TokenDep, application_id: int, status: schemas.ApplicationStatus, db: Session = Depends(get_db)):
    return crud_application.update_application_status(db, application_id, status)

@router.put("/{application_id}/response", response_model=schemas.ApplicationBase)
def update_application_response(_: TokenDep, application_id: int, user_response: schemas.UserResponse, db: Session = Depends(get_db)):
    return crud_application.update_application_response(db, application_id, user_response)

@router.get("/scholarship/{scholarship_id}", response_model=List[schemas.ApplicationBase])
def get_applications_by_scholarship(_: TokenDep, scholarship_id: int, db: Session = Depends(get_db)):
    return crud_application.get_applications_by_scholarship(db, scholarship_id)

### SQS HANDLING ###

sqs = boto3.client(
    'sqs',
    aws_access_key_id=AWS_ACESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
def process_message(message):
    # Add your message processing logic here    
    notification = json.loads(message['Body'])
    applications = crud_application.get_applications_by_scholarship(next(get_db()), notification["scholarship_id"])
    for application in applications:
        crud_application.update_application_status(next(get_db()), application.id, schemas.ApplicationStatus.under_evaluation)

    # Remove unwanted applications attributes
    applications = [application.dict() for application in applications]
    for application in applications:
        application.pop("status")
        application["created_at"] = application["created_at"].isoformat()

    message = {
        "applications": applications,
        "scholarship_id": notification["scholarship_id"],
        "jury_ids": notification["jury_ids"],
        "spots": notification["spots"],
        "closed_at": notification["closed_at"]
    }
    logging.info(f"Sending message to grading: {message}")
    send_to_sqs(message)
    
def send_to_sqs(message: dict):
    response = sqs.send_message(
        QueueUrl=TO_GRADING_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    print(f"Message sent to SQS: {response['MessageId']}")
    return response

def receive_message(queue_url):
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5,
    )
    messages = response.get('Messages', [])
    for message in messages:
        body = json.loads(message['Body'])
        logging.info(f"Received message: {body}")
        process_message(message)
        # Delete the message from the queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )

scheduler = BackgroundScheduler()
scheduler.add_job(receive_message, 'interval', seconds=2, max_instances=10, args=[DEADLINE_QUEUE_URL])
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
scheduler.start()