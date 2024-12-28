from sqlalchemy.orm import Session
from app.schemas import schemas
from app.models import models

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

def update_application_status(db: Session, application_id: int, status: schemas.ApplicationStatus):
    db_application = db.query(models.Application).filter(models.Application.id == application_id).first()
    db_application.status = status
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