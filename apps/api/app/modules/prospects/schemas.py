from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.modules.prospects.domain.enums import PersonType, ProspectStatus, RelationshipType
from app.shared.schemas import ApiModel


class TagRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    name: str
    color: str | None
    description: str | None


class TagCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    color: str | None = Field(default=None, max_length=9)
    description: str | None = Field(default=None, max_length=500)


class ProspectContactRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    full_name: str
    position: str | None
    area: str | None
    email: str | None
    phone: str | None
    whatsapp: str | None
    is_primary: bool
    notes: str | None


class ProspectContactCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    position: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    whatsapp: str | None = Field(default=None, max_length=30)
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class ProspectAssignmentRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    from_user: "UserTiny | None"
    to_user: "UserTiny"
    assigned_by: "UserTiny | None"
    reason: str | None
    assigned_at: datetime


class ProspectStatusHistoryRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    from_relationship_type: RelationshipType | None
    to_relationship_type: RelationshipType
    from_status: ProspectStatus | None
    to_status: ProspectStatus
    changed_by: "UserTiny | None"
    reason: str | None
    created_at: datetime


class UserTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    full_name: str
    email: str


class ProspectRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    person_type: PersonType
    document_type: "CatalogOptionTiny | None"
    document_number: str | None
    first_name: str | None
    last_name: str | None
    birth_date: date | None
    legal_name: str | None
    trade_name: str | None
    display_name: str
    email: str | None
    phone: str | None
    phone_alt: str | None
    whatsapp: str | None
    address: str | None
    source: "CatalogOptionTiny | None"
    acquisition_channel: "CatalogOptionTiny | None"
    interest_level: "CatalogOptionTiny | None"
    priority: "CatalogOptionTiny | None"
    relationship_type: RelationshipType
    status: ProspectStatus
    converted_at: datetime | None
    converted_by: UserTiny | None
    owner: UserTiny
    next_action_at: datetime | None
    next_action_desc: str | None
    interaction_count: int
    score: Decimal
    notes: str | None
    tags: list[TagRead]
    contacts: list[ProspectContactRead]
    created_at: datetime
    updated_at: datetime


class CatalogOptionTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    color: str | None


class ProspectCreate(BaseModel):
    person_type: PersonType
    document_type_id: UUID | None = None
    document_number: str | None = Field(default=None, max_length=20)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    legal_name: str | None = Field(default=None, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    phone_alt: str | None = Field(default=None, max_length=30)
    whatsapp: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=1000)
    source_id: UUID | None = None
    acquisition_channel_id: UUID | None = None
    interest_level_id: UUID | None = None
    priority_id: UUID | None = None
    owner_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[UUID] = Field(default_factory=list)
    contacts: list[ProspectContactCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_names(self) -> "ProspectCreate":
        if self.person_type == PersonType.NATURAL:
            if not self.first_name or not self.last_name:
                raise ValueError("Persona natural requiere nombres y apellidos")
        else:
            if not self.legal_name:
                raise ValueError("Persona jurídica requiere razón social")
        return self


class ProspectUpdate(BaseModel):
    document_type_id: UUID | None = None
    document_number: str | None = Field(default=None, max_length=20)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    legal_name: str | None = Field(default=None, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    phone_alt: str | None = Field(default=None, max_length=30)
    whatsapp: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=1000)
    source_id: UUID | None = None
    acquisition_channel_id: UUID | None = None
    interest_level_id: UUID | None = None
    priority_id: UUID | None = None
    status: ProspectStatus | None = None
    status_reason: str | None = Field(default=None, max_length=500)
    owner_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[UUID] | None = None
    contacts: list[ProspectContactCreate] | None = None


class ProspectFilters(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    person_type: PersonType | None = None
    status: ProspectStatus | None = None
    relationship_type: RelationshipType | None = None
    owner_id: UUID | None = None
    interest_level_id: UUID | None = None
    priority_id: UUID | None = None
    source_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)


class DuplicateCheckRequest(BaseModel):
    person_type: PersonType | None = None
    document_type_id: UUID | None = None
    document_number: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    name: str | None = Field(default=None, max_length=200)


class DuplicateMatch(ApiModel):
    prospect_id: UUID
    code: str
    display_name: str
    field: str
    match_type: str  # exact | similar


class DuplicateCheckResult(BaseModel):
    blocked: bool
    block_reason: str | None = None
    matches: list[DuplicateMatch]


class StatusChangeRequest(BaseModel):
    status: ProspectStatus
    reason: str = Field(min_length=3, max_length=500)


class AssignRequest(BaseModel):
    owner_id: UUID
    reason: str | None = Field(default=None, max_length=500)


class BulkAssignRequest(BaseModel):
    prospect_ids: list[UUID] = Field(min_length=1, max_length=200)
    owner_id: UUID
    reason: str | None = Field(default=None, max_length=500)
