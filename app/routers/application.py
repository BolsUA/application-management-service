from typing import List, Dict, Annotated
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas import schemas
from app.crud import crud_application
from app.core.config import settings
import jwt
from jwt import PyJWKClient

router = APIRouter()

oauth2_scheme = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    
    try:
        # Fetch public keys from AWS Cognito
        jwks_client = PyJWKClient(settings.COGNITO_KEYS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and validate the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.CLIENT_ID,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWKError:
        raise HTTPException(status_code=401, detail="Invalid token")

TokenDep = Annotated[Dict, Depends(verify_token)]

# applications variable cant be a schemas because of the argument document_file...
@router.post("/", response_model=schemas.ApplicationBase)
def create_application(
        token: TokenDep,
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
        crud_application.create_application_document(db, db_application.id, document[1])

    return db_application

@router.get("/", response_model=list[schemas.ApplicationBase])
def get_applications(token: TokenDep, user_id: str, db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return crud_application.get_applications(db, user_id, skip, limit)

@router.get("/{application_id}/details", response_model=schemas.ApplicationBase)
def get_application(token: TokenDep, application_id: int, db: Session = Depends(get_db)):
    return crud_application.get_application(db, application_id)

@router.put("/{application_id}/status", response_model=schemas.ApplicationBase)
def update_application_status(token: TokenDep, application_id: int, status: schemas.ApplicationStatus, db: Session = Depends(get_db)):
    return crud_application.update_application_status(db, application_id, status)

