from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy.sql import func
from enum import Enum

class ApplicationStatus(str, Enum):
    submitted = "Submitted"
    under_evaluation = "Under Evaluation"
    approved = "Approved"
    rejected = "Rejected"

class UserResponse(str, Enum):
    accept = "Accepted"
    reject = "Declined"

class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: str = Field(nullable=False)
    scholarship_id: int = Field(nullable=False)
    name: str = Field(nullable=False)
    created_at: datetime = Field(default=func.now(), nullable=False)
    status: ApplicationStatus = Field(nullable=False, default=ApplicationStatus.submitted)
    user_response: Optional[UserResponse] = Field(default=None)
    grade: Optional[float] = Field(default=None, nullable=True)
    reason: Optional[str] = Field(default=None, nullable=True)
    
    documents: List["DocumentTemplate"] = Relationship(back_populates="application")

class DocumentTemplate(SQLModel, table=True):

    id:  Optional[int] = Field(default=None, primary_key=True, index=True)
    application_id: Optional[int] = Field(foreign_key="application.id")
    name: str = Field(nullable=False)
    file_path: str = Field(nullable=False)
    
    application: Optional[Application] = Relationship(back_populates="documents")
