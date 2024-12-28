import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import schemas
from app.crud import crud_application
import json

router = APIRouter()

# applications variable cant be a schemas because of the argument document_file...
@router.post("/", response_model=schemas.ApplicationBase)
def create_application(
        scholarship_id: int = Form(...),
        user_id: str = Form(...),
        status: schemas.ApplicationStatus = Form(schemas.ApplicationStatus.submitted),
        name: str = Form(...),
        document_file: List[UploadFile] = File(None),
        db: Session = Depends(get_db),
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
        create_document(db, db_application.id, document[1])

    return db_application

@router.get("/", response_model=list[schemas.ApplicationBase])
def get_applications(user_id: str, db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return crud_application.get_applications(db, user_id, skip, limit)

@router.get("/{application_id}/details", response_model=schemas.ApplicationBase)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return crud_application.get_application(db, application_id)

@router.put("/{application_id}/status", response_model=schemas.ApplicationBase)
def update_application_status(application_id: int, status: schemas.ApplicationStatus, db: Session = Depends(get_db)):
    return crud_application.update_application_status(db, application_id, status)


def create_document(db: Session, application_id: int, file: UploadFile) -> schemas.DocumentTemplate:
    
    document_name = get_filename_without_extension(file)

    if not document_name:
        raise HTTPException(status_code=400, detail="Document name could not be determined")

    # Save the document file
    file_location = ""
    file_location = save_file(file, "application_files")
    
    if not file_location:
        raise HTTPException(status_code=500, detail="Could not save document file")
    
    # Create the document template record
    return crud_application.create_document(db, application_id, document_name, file_location)

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