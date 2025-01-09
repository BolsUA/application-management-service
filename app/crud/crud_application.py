import os
import shutil
import boto3
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.schemas import schemas
from app.models import models
from fastapi import HTTPException, UploadFile
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from app.core.config import settings

s3_client = boto3.client(
    "s3",
    region_name=settings.REGION,
)

def create_application(db: Session, application: schemas.ApplicationBase):
    db_application = models.Application(
        user_id=application.user_id,
        scholarship_id=application.scholarship_id,
        name=application.name
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_applications(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.Application).filter(models.Application.user_id == user_id).offset(skip).limit(limit).all()

def get_application(db: Session, application_id: int):
    return db.query(models.Application).filter(models.Application.id == application_id).first()

def update_application_status(db: Session, application_id: int, status: schemas.ApplicationStatus, grade: float = None, reason: str = None):
    db_application = db.query(models.Application).filter(models.Application.id == application_id).first()
    db_application.status = status
    if grade is not None:
        db_application.grade = grade
    if reason is not None:
        db_application.reason = reason
    db.commit()
    db.refresh(db_application)
    return db_application

def create_document(db: Session, application_id: int, document_name: str, file_location: str):
    # Create the document template record
    new_document = models.DocumentTemplate(
        application_id=application_id,
        name=document_name,
        file_path=file_location
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document

async def create_application_document(db: Session, application_id: int, file: UploadFile) -> models.DocumentTemplate:
    
    document_name = get_filename_without_extension(file)

    if not document_name:
        raise HTTPException(status_code=400, detail="Document name could not be determined")

    # Save the document file
    file_location = await save_file(file)
    
    if not file_location:
        raise HTTPException(status_code=500, detail="Could not save document file")
    
    # Create the document template record
    return create_document(db, application_id, document_name, get_file_url(file_location))

def get_filename_without_extension(file: UploadFile) -> str:
    if file is None or file.filename is None:
        return None
    # Split the filename into the name and extension
    filename, _ = os.path.splitext(file.filename)
    return filename

def get_file_url(filename: str) -> str:
    try:
        print("Getting file URL: ", filename)
        # Generate pre-signed URL - this is synchronous
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": filename},
            ExpiresIn=100000,
        )
        return url
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail=f"File {filename} not found in bucket.")
    except (NoCredentialsError, PartialCredentialsError):
        raise HTTPException(status_code=500, detail="Invalid AWS credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def save_file(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a valid filename.")
    
    try:
        file_content = await file.read()  # This needs to be awaited as it's from FastAPI
        key = str(file.filename)
        # This is synchronous and doesn't need await
        s3_client.put_object(
            Bucket=str(settings.S3_BUCKET_NAME),
            Key=key,
            Body=file_content
        )
        return key
    except (NoCredentialsError, PartialCredentialsError):
        raise HTTPException(status_code=500, detail="Invalid AWS credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

# def save_file(file: UploadFile, directory: str) -> str:
#     # Create the directory if it doesn't exist
#     if not file.filename:
#         raise HTTPException(status_code=400, detail="File must have a valid filename.")
#
#     os.makedirs(directory, exist_ok=True)
#
#     # Sanitize the filename to prevent directory traversal attacks
#     filename = os.path.basename(file.filename)
#     if filename != file.filename or '..' in filename or filename.startswith('/'):
#         raise HTTPException(status_code=400, detail="Invalid filename.")
#
#     file_path = os.path.join(directory, filename)
#
#     print(filename)
#     try:
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#     except Exception:
#         raise HTTPException(status_code=500, detail="Could not save file.")
#
#     file_path = os.path.join(directory, file.filename)
#     # with open(file_path, "wb") as f:
#     #     f.write(file.file.read())
#     return file_path

def get_applications_by_scholarship(db: Session, scholarship_id: int):
    try:
        applications = db.query(models.Application).filter(
            models.Application.scholarship_id == scholarship_id
        ).all()
        if not applications:
            print(f"No applications found for scholarship_id {scholarship_id}")
        return applications
    except Exception as e:
        print(e)
        raise

def update_application_select(db: Session, application_id: int, select: bool):
    db_application = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    db_application.select = select
    db.commit()
    db.refresh(db_application)
    return db_application

def get_all_applications(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Application).offset(skip).limit(limit).all()