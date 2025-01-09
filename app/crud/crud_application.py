import os
import shutil
from sqlalchemy.orm import Session
from app.schemas import schemas
from app.models import models
from fastapi import HTTPException, UploadFile


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

def update_application_status(db: Session, application_id: int, status: schemas.ApplicationStatus, grade: float, reason: str):
    db_application = db.query(models.Application).filter(models.Application.id == application_id).first()
    db_application.status = status
    db_application.grade = grade
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

def create_application_document(db: Session, application_id: int, file: UploadFile) -> models.DocumentTemplate:
    
    document_name = get_filename_without_extension(file)

    if not document_name:
        raise HTTPException(status_code=400, detail="Document name could not be determined")

    # Save the document file
    file_location = ""
    file_location = save_file(file, "application_files")
    
    if not file_location:
        raise HTTPException(status_code=500, detail="Could not save document file")
    
    # Create the document template record
    return create_document(db, application_id, document_name, file_location)

def get_filename_without_extension(file: UploadFile) -> str:
    if file is None or file.filename is None:
        return None
    # Split the filename into the name and extension
    filename, _ = os.path.splitext(file.filename)
    return filename

def save_file(file: UploadFile, directory: str) -> str:
    # Create the directory if it doesn't exist
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a valid filename.")

    os.makedirs(directory, exist_ok=True)

    # Sanitize the filename to prevent directory traversal attacks
    filename = os.path.basename(file.filename)
    if filename != file.filename or '..' in filename or filename.startswith('/'):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = os.path.join(directory, filename)

    print(filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save file.")

    file_path = os.path.join(directory, file.filename)
    # with open(file_path, "wb") as f:
    #     f.write(file.file.read())
    return file_path

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
