from typing import List, Optional, Any
from pydantic import BaseModel, Field


# Domain Models
class DomainBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = ""
    icon: Optional[str] = "folder"
    color: Optional[str] = "indigo"
    order_index: Optional[int] = 0


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    order_index: Optional[int] = None


class DomainResponse(DomainBase):
    id: int
    topic_count: Optional[int] = 0
    resource_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Topic Models
class TopicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    domain_id: int
    parent_id: Optional[int] = None
    slug: Optional[str] = None
    summary: Optional[str] = ""
    status: Optional[str] = "in_progress"  # 'not_started', 'in_progress', 'mastered', 'reference'
    importance: Optional[str] = "high"     # 'core', 'high', 'medium', 'low'
    drive_folder_url: Optional[str] = ""
    order_index: Optional[int] = 0


class TopicCreate(TopicBase):
    pass


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    domain_id: Optional[int] = None
    parent_id: Optional[int] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    importance: Optional[str] = None
    drive_folder_url: Optional[str] = None
    order_index: Optional[int] = None


class TopicResponse(TopicBase):
    id: int
    domain_name: Optional[str] = None
    domain_color: Optional[str] = None
    resource_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Resource Models
class ResourceBase(BaseModel):
    topic_id: int
    type: str  # 'youtube', 'drive_folder', 'drive_file', 'pdf', 'note', 'article', 'github'
    title: str = Field(..., min_length=1, max_length=200)
    url: Optional[str] = ""
    file_path: Optional[str] = ""
    notes: Optional[str] = ""
    tags: Optional[List[str]] = []
    is_favorite: Optional[bool] = False
    order_index: Optional[int] = 0


class ResourceCreate(ResourceBase):
    pass


class BulkResourceCreate(BaseModel):
    domain_id: int
    topic_id: Optional[int] = None
    type: str = "youtube"
    links_text: Optional[str] = ""
    links: Optional[List[str]] = []


class ResourceUpdate(BaseModel):
    topic_id: Optional[int] = None
    type: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    order_index: Optional[int] = None


class ResourceResponse(BaseModel):
    id: int
    topic_id: int
    type: str
    title: str
    url: Optional[str] = ""
    file_path: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[str] = []
    is_favorite: bool = False
    order_index: int = 0
    topic_title: Optional[str] = None
    domain_name: Optional[str] = None
    domain_color: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Auth Models
class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=4)


class AuthStatusResponse(BaseModel):
    authenticated: bool
    auth_enabled: bool
    site_title: str
