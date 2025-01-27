from typing import List, Dict, Annotated
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import get_db
from app.models import models
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
APP_GRADING_QUEUE_URL = str(os.getenv("APP_GRADING_QUEUE_URL"))
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
@router.post("/submit", response_model=schemas.ApplicationBase)
async def create_application(
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
        await crud_application.create_application_document(db, db_application.id, document[1])

    return db_application

@router.get("/", response_model=list[schemas.ApplicationBase])
def get_applications(_: TokenDep, user_id: str, db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return crud_application.get_applications(db, user_id, skip, limit)

@router.get("/{application_id}/details", response_model=schemas.ApplicationBase)
def get_application(_: TokenDep, application_id: int, db: Session = Depends(get_db)):
    return crud_application.get_application(db, application_id)

#@router.put("/{application_id}/status", response_model=schemas.ApplicationBase)
def update_application_status(application_id: int, status: schemas.ApplicationStatus, grade: float, reason: str, db: Session = Depends(get_db)):
    return crud_application.update_application_status(db, application_id, status, grade, reason)

@router.get("/scholarship/{scholarship_id}", response_model=List[schemas.ApplicationBase])
def get_applications_by_scholarship(_: TokenDep, scholarship_id: int, db: Session = Depends(get_db)):
    return crud_application.get_applications_by_scholarship(db, scholarship_id)

### SQS HANDLING ###

sqs = boto3.client(
    'sqs',
    region_name=REGION
)
def process_message(message):
    notification = json.loads(message['Body'])
    # Use joinedload to eagerly load the documents relationship
    db = next(get_db())
    applications = (
        db.query(models.Application)
        .options(joinedload(models.Application.documents))
        .filter(models.Application.scholarship_id == notification["scholarship_id"])
        .all()
    )
    
    for application in applications:
        crud_application.update_application_status(
            db, 
            application.id, 
            schemas.ApplicationStatus.under_evaluation
        )

    logging.info(f"Applications under evaluation: {applications}")

    # Convert applications to dict with documents included
    applications_data = []
    for application in applications:
        app_dict = application.model_dump()
        # Convert documents to dict format
        documents_data = []
        for doc in application.documents:
            doc_dict = {
                "id": doc.id,
                "name": doc.name,
                "file_path": doc.file_path
            }
            documents_data.append(doc_dict)
        
        # Remove unwanted attributes and add documents
        app_dict.pop("status")
        app_dict["created_at"] = app_dict["created_at"].isoformat()
        app_dict["documents"] = documents_data
        applications_data.append(app_dict)

    logging.info(f"Applications to be graded: {applications_data}")

    message = {
        "applications": applications_data,
        "scholarship_id": notification["scholarship_id"],
        "jury_ids": notification["jury_ids"],
        "spots": notification["spots"],
        "closed_at": notification["closed_at"]
    }
    logging.info(f"Sending message to grading: {message}")
    send_to_sqs(message)

def process_message2(message):
    # Add your message processing logic here
    notification = json.loads(message['Body'])
    for application in notification["applications"]:
        application_id = application['application_id']
        status = application['status']
        grade = application['grade']
        reason = application['reason']
        #### THE WINNER MUST HAVE FLAG SELECTED SET TO TRUE 
        if(status == "Accepted"):
            status = schemas.ApplicationStatus.approved
            crud_application.update_application_select(next(get_db()), application_id, True)
        else:
            status = schemas.ApplicationStatus.rejected
            crud_application.update_application_select(next(get_db()), application_id, False)
        crud_application.update_application_status(next(get_db()), application_id, status, grade, reason)
        logging.info(f"Updated application {application_id} status to {status} with grade {grade}, reason: {reason}") 
    
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
        if queue_url == DEADLINE_QUEUE_URL:
            process_message(message)
        if queue_url == APP_GRADING_QUEUE_URL:
            process_message2(message)
        # Delete the message from the queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )

scheduler = BackgroundScheduler()
scheduler.add_job(receive_message, 'interval', seconds=2, max_instances=10, args=[DEADLINE_QUEUE_URL])
scheduler.add_job(receive_message, 'interval', seconds=2, max_instances=10, args=[APP_GRADING_QUEUE_URL])
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
scheduler.start()
