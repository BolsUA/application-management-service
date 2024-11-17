from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class DocumentTemplateBase(BaseModel):
    name: str
    file_path: str

class DocumentTemplateCreate(DocumentTemplateBase):
    pass

class DocumentTemplate(DocumentTemplateBase):
    id: int
    application_id: int

    class Config:
        from_attributes = True

class ApplicationStatus(str, Enum):
    #draft = "Draft"
    submitted = "Submitted"
    under_evaluation = "Under Evaluation"
    approved = "Approved"
    rejected = "Rejected"
    graded = "Graded"

class ApplicationBase(BaseModel):
    id: int
    scholarship_id: int
    user_id: str
    status: ApplicationStatus = ApplicationStatus.submitted
    created_at: Optional[datetime] = None
    name: str
    documents: Optional[List[DocumentTemplateCreate]] = None