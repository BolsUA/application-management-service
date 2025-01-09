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

class UserResponse(str, Enum):
    accept = "Accepted"
    reject = "Declined"

class ApplicationStatus(str, Enum):
    #draft = "Draft"
    submitted = "Submitted"
    under_evaluation = "Under Evaluation"
    approved = "Approved" # if approved means that is graded and selected for the position
    rejected = "Rejected" # if reject means that is graded but wasn't chosen for the position
    # graded = "Graded"

class ApplicationBase(BaseModel):
    id: int
    scholarship_id: int
    user_id: str
    status: ApplicationStatus = ApplicationStatus.submitted
    created_at: Optional[datetime] = None
    name: str
    documents: Optional[List[DocumentTemplateCreate]] = None
    user_response: Optional[UserResponse] = None
    grade: Optional[float] = None 
    selected: bool = False
