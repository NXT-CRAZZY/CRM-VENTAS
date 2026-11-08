from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.catalogs.infrastructure.models import CatalogOption
from app.modules.prospects.domain.enums import PersonType, ProspectStatus, RelationshipType
from app.modules.prospects.domain.errors import DuplicateDocumentError, InvalidDocumentError
from app.modules.prospects.infrastructure.models import Prospect, ProspectAssignment, ProspectStatusHistory, Tag
from app.modules.prospects.repository import ProspectRepository
from app.modules.prospects.schemas import (
    AssignRequest,
    BulkAssignRequest,
    DuplicateCheckRequest,
    DuplicateCheckResult,
    DuplicateMatch,
    ProspectAssignmentRead,
    ProspectCreate,
    ProspectFilters,
    ProspectRead,
    ProspectStatusHistoryRead,
    ProspectUpdate,
    StatusChangeRequest,
    TagCreate,
    TagRead,
)
from app.modules.users.infrastructure.models import User
from app.shared.documents import is_valid_dni, is_valid_ruc, ruc_person_type
from app.shared.pagination import Page, PageParams


def _display_name(person_type: PersonType, data: ProspectCreate | ProspectUpdate) -> str:
    if person_type == PersonType.NATURAL:
        parts = [data.first_name or "", data.last_name or ""]
        return " ".join(p.strip() for p in parts if p.strip())
    return (data.legal_name or "").strip() or (data.trade_name or "").strip()


def _snapshot(p: Prospect) -> dict:
    return {
        "code": p.code,
        "person_type": p.person_type,
        "document_number": p.document_number,
        "display_name": p.display_name,
        "email": p.email,
        "phone": p.phone,
        "status": p.status,
        "relationship_type": p.relationship_type,
        "owner_id": str(p.owner_id),
        "interest_level_id": p.interest_level_id,
        "priority_id": p.priority_id,
    }


class ProspectService:
    def __init__(self, repo: ProspectRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    # ---- Tags ----
    def list_tags(self) -> list[TagRead]:
        from sqlalchemy import select

        tags = self.repo.s.scalars(select(Tag).order_by(Tag.name))
        return [TagRead.model_validate(t) for t in tags]

    def create_tag(self, data: TagCreate) -> TagRead:
        from sqlalchemy import select

        existing = self.repo.s.scalar(select(Tag).where(Tag.name.ilike(data.name.strip())))
        if existing:
            raise ConflictError("Ya existe una etiqueta con ese nombre.", code="TAG_NAME_TAKEN")
        tag = Tag(name=data.name.strip(), color=data.color, description=data.description)
        self.repo.s.add(tag)
        self.repo.s.flush()
        if self.audit:
            self.audit.record("tag.created", "tag", tag.public_id, label=tag.name)
        return TagRead.model_validate(tag)

    # ---- Prospectos ----
    def _resolve_ids(self, data: ProspectCreate | ProspectUpdate) -> dict:
        out: dict = {}
        if data.document_type_id:
            out["document_type_id"] = self.repo.get_catalog_option_id(data.document_type_id)
        elif data.document_number:
            # Inferir tipo de documento del tipo de persona si no se envió explícitamente.
            inferred = "RUC" if data.person_type == PersonType.JURIDICA else "DNI"
            out["document_type_id"] = self.repo.get_catalog_option_id_by_code("document_type", inferred)
        if data.source_id:
            out["source_id"] = self.repo.get_catalog_option_id(data.source_id)
        if data.acquisition_channel_id:
            out["acquisition_channel_id"] = self.repo.get_catalog_option_id(data.acquisition_channel_id)
        if data.interest_level_id:
            out["interest_level_id"] = self.repo.get_catalog_option_id(data.interest_level_id)
        if data.priority_id:
            out["priority_id"] = self.repo.get_catalog_option_id(data.priority_id)
        if hasattr(data, "owner_id") and data.owner_id:
            out["owner_id"] = self.repo.get_user_id(data.owner_id)
        return out

    def _validate_document(self, person_type: PersonType, document_type_id: int | None, document_number: str | None) -> None:
        if not document_number:
            return
        doc_type = None
        if document_type_id:
            doc_type = self.repo.s.scalar(
                select(CatalogOption).where(CatalogOption.id == document_type_id)
            )
        if doc_type and doc_type.code == "RUC":
            if not is_valid_ruc(document_number):
                raise InvalidDocumentError("El RUC no es válido (11 dígitos y dígito verificador).")
            if person_type == PersonType.NATURAL and ruc_person_type(document_number) != PersonType.NATURAL:
                raise InvalidDocumentError("El RUC ingresado corresponde a persona jurídica, no natural.")
            if person_type == PersonType.JURIDICA and ruc_person_type(document_number) != PersonType.JURIDICA:
                raise InvalidDocumentError("El RUC ingresado corresponde a persona natural con negocio, no jurídica.")
        elif doc_type and doc_type.code == "DNI":
            if not is_valid_dni(document_number):
                raise InvalidDocumentError("El DNI debe tener 8 dígitos numéricos.")

    def _prospect(self, public_id: UUID) -> Prospect:
        prospect = self.repo.get_prospect(public_id)
        if prospect is None:
            raise NotFoundError("El prospecto no existe.")
        return prospect

    def _enforce_scope(self, prospect: Prospect, user: User) -> None:
        if P.PROSPECTS_READ_ALL in user.permission_codes:
            return
        if prospect.owner_id != user.id:
            raise ForbiddenError("No tienes acceso a este prospecto.")

    def create_prospect(self, data: ProspectCreate, actor: User) -> ProspectRead:
        resolved = self._resolve_ids(data)
        self._validate_document(data.person_type, resolved.get("document_type_id"), data.document_number)

        if resolved.get("document_type_id") and data.document_number:
            existing = self.repo.get_prospect_by_document(resolved["document_type_id"], data.document_number)
            if existing:
                raise DuplicateDocumentError("Ya existe un prospecto con ese documento.")

        owner_id = resolved.get("owner_id") or actor.id
        display = _display_name(data.person_type, data)

        prospect = Prospect(
            code=self.repo.next_code(),
            person_type=data.person_type.value,
            document_type_id=resolved.get("document_type_id"),
            document_number=data.document_number.upper() if data.document_number else None,
            first_name=(data.first_name or "").strip() if data.first_name else None,
            last_name=(data.last_name or "").strip() if data.last_name else None,
            birth_date=data.birth_date,
            legal_name=(data.legal_name or "").strip() if data.legal_name else None,
            trade_name=(data.trade_name or "").strip() if data.trade_name else None,
            display_name=display,
            email=(data.email or "").lower().strip() if data.email else None,
            phone=(data.phone or "").strip() if data.phone else None,
            phone_alt=(data.phone_alt or "").strip() if data.phone_alt else None,
            whatsapp=(data.whatsapp or "").strip() if data.whatsapp else None,
            address=(data.address or "").strip() if data.address else None,
            source_id=resolved.get("source_id"),
            acquisition_channel_id=resolved.get("acquisition_channel_id"),
            interest_level_id=resolved.get("interest_level_id"),
            priority_id=resolved.get("priority_id"),
            owner_id=owner_id,
            notes=data.notes,
        )
        prospect.tags = self.repo.get_tags_by_public_ids(data.tags)
        for c in data.contacts:
            prospect.contacts.append(
                ProspectContact(
                    full_name=c.full_name.strip(),
                    position=(c.position or "").strip() if c.position else None,
                    area=(c.area or "").strip() if c.area else None,
                    email=(c.email or "").lower().strip() if c.email else None,
                    phone=(c.phone or "").strip() if c.phone else None,
                    whatsapp=(c.whatsapp or "").strip() if c.whatsapp else None,
                    is_primary=c.is_primary,
                    notes=c.notes,
                )
            )

        self.repo.add_prospect(prospect)
        self.repo.add_status_history(
            ProspectStatusHistory(
                prospect_id=prospect.id,
                to_relationship_type=prospect.relationship_type,
                to_status=prospect.status,
                changed_by_id=actor.id,
                reason="Creación del prospecto",
            )
        )
        self.repo.add_assignment(
            ProspectAssignment(
                prospect_id=prospect.id,
                to_user_id=owner_id,
                assigned_by_id=actor.id,
                reason="Creación del prospecto",
            )
        )
        if self.audit:
            self.audit.record(
                "prospect.created",
                "prospect",
                prospect.public_id,
                label=prospect.display_name,
                after=_snapshot(prospect),
            )
        return ProspectRead.model_validate(prospect)

    def get_prospect(self, public_id: UUID, user: User) -> ProspectRead:
        prospect = self._prospect(public_id)
        self._enforce_scope(prospect, user)
        return ProspectRead.model_validate(prospect)

    def get_prospect_assignments(self, public_id: UUID, user: User) -> list[ProspectAssignmentRead]:
        prospect = self._prospect(public_id)
        self._enforce_scope(prospect, user)
        return [ProspectAssignmentRead.model_validate(a) for a in self.repo.get_prospect_assignments(public_id)]

    def get_prospect_status_history(self, public_id: UUID, user: User) -> list[ProspectStatusHistoryRead]:
        prospect = self._prospect(public_id)
        self._enforce_scope(prospect, user)
        return [ProspectStatusHistoryRead.model_validate(h) for h in self.repo.get_prospect_status_history(public_id)]

    def list_prospects(self, filters: ProspectFilters, params: PageParams, user: User) -> Page[ProspectRead]:
        accessible = None
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            accessible = [user.id]
        items, total = self.repo.list_prospects(filters, params, accessible)
        return Page[ProspectRead](
            items=[ProspectRead.model_validate(p) for p in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def update_prospect(self, public_id: UUID, data: ProspectUpdate, actor: User) -> ProspectRead:
        prospect = self._prospect(public_id)
        if P.PROSPECTS_UPDATE_ALL not in actor.permission_codes and prospect.owner_id != actor.id:
            raise ForbiddenError("No puedes editar este prospecto.")

        before = _snapshot(prospect)
        resolved = self._resolve_ids(data)

        if resolved.get("document_type_id") and data.document_number:
            existing = self.repo.get_prospect_by_document(resolved["document_type_id"], data.document_number)
            if existing and existing.id != prospect.id:
                raise DuplicateDocumentError("Ya existe otro prospecto con ese documento.")

        self._validate_document(
            PersonType(prospect.person_type),
            resolved.get("document_type_id") or prospect.document_type_id,
            data.document_number or prospect.document_number,
        )

        simple_fields = {
            "document_type_id": resolved.get("document_type_id"),
            "document_number": (data.document_number.upper() if data.document_number else None),
            "first_name": (data.first_name.strip() if data.first_name else None),
            "last_name": (data.last_name.strip() if data.last_name else None),
            "birth_date": data.birth_date,
            "legal_name": (data.legal_name.strip() if data.legal_name else None),
            "trade_name": (data.trade_name.strip() if data.trade_name else None),
            "email": (data.email.lower().strip() if data.email else None),
            "phone": (data.phone.strip() if data.phone else None),
            "phone_alt": (data.phone_alt.strip() if data.phone_alt else None),
            "whatsapp": (data.whatsapp.strip() if data.whatsapp else None),
            "address": (data.address.strip() if data.address else None),
            "source_id": resolved.get("source_id"),
            "acquisition_channel_id": resolved.get("acquisition_channel_id"),
            "interest_level_id": resolved.get("interest_level_id"),
            "priority_id": resolved.get("priority_id"),
            "notes": data.notes,
        }
        for field, value in simple_fields.items():
            if value is not None or (data.model_dump(exclude_unset=True).get(field) is not None):
                setattr(prospect, field, value)

        prospect.display_name = _display_name(
            PersonType(prospect.person_type),
            ProspectCreate(
                person_type=PersonType(prospect.person_type),
                first_name=prospect.first_name,
                last_name=prospect.last_name,
                legal_name=prospect.legal_name,
                trade_name=prospect.trade_name,
                owner_id=None,
            ),
        )

        if data.tags is not None:
            prospect.tags = self.repo.get_tags_by_public_ids(data.tags)

        if data.contacts is not None:
            prospect.contacts = [
                ProspectContact(
                    full_name=c.full_name.strip(),
                    position=(c.position or "").strip() if c.position else None,
                    area=(c.area or "").strip() if c.area else None,
                    email=(c.email or "").lower().strip() if c.email else None,
                    phone=(c.phone or "").strip() if c.phone else None,
                    whatsapp=(c.whatsapp or "").strip() if c.whatsapp else None,
                    is_primary=c.is_primary,
                    notes=c.notes,
                )
                for c in data.contacts
            ]

        if data.status is not None and data.status.value != prospect.status:
            old_status = prospect.status
            prospect.status = data.status.value
            self.repo.add_status_history(
                ProspectStatusHistory(
                    prospect_id=prospect.id,
                    from_relationship_type=prospect.relationship_type,
                    to_relationship_type=prospect.relationship_type,
                    from_status=old_status,
                    to_status=prospect.status,
                    changed_by_id=actor.id,
                    reason=data.status_reason or "Cambio de estado",
                )
            )

        if resolved.get("owner_id") and resolved["owner_id"] != prospect.owner_id:
            self.assign_prospect(public_id, AssignRequest(owner_id=UUID(int=resolved["owner_id"]), reason="Reasignación por edición"), actor)

        self.repo.add_prospect(prospect)
        if self.audit:
            from app.modules.audit.application.recorder import diff

            b, a = diff(before, _snapshot(prospect))
            if a:
                self.audit.record(
                    "prospect.updated",
                    "prospect",
                    prospect.public_id,
                    label=prospect.display_name,
                    before=b,
                    after=a,
                )
        return ProspectRead.model_validate(prospect)

    def delete_prospect(self, public_id: UUID, actor: User) -> None:
        prospect = self._prospect(public_id)
        if P.PROSPECTS_DELETE not in actor.permission_codes:
            raise ForbiddenError("No tienes permiso para eliminar prospectos.")
        prospect.deleted_at = datetime.now()
        self.repo.add_prospect(prospect)
        if self.audit:
            self.audit.record(
                "prospect.deleted",
                "prospect",
                prospect.public_id,
                label=prospect.display_name,
                before={"deleted_at": None},
                after={"deleted_at": prospect.deleted_at.isoformat()},
            )

    def check_duplicates(self, request: DuplicateCheckRequest, exclude_public_id: UUID | None = None) -> DuplicateCheckResult:
        matches = self.repo.find_duplicates(request, exclude_public_id)
        blocked = any(m["field"] == "documento" and m["type"] == "exact" for m in matches)
        return DuplicateCheckResult(
            blocked=blocked,
            block_reason="Ya existe un prospecto con ese documento." if blocked else None,
            matches=[
                DuplicateMatch(
                    prospect_id=m["prospect"].public_id,
                    code=m["prospect"].code,
                    display_name=m["prospect"].display_name,
                    field=m["field"],
                    match_type=m["type"],
                )
                for m in matches
            ],
        )

    def assign_prospect(self, public_id: UUID, request: AssignRequest, actor: User) -> ProspectRead:
        prospect = self._prospect(public_id)
        if P.PROSPECTS_ASSIGN not in actor.permission_codes:
            raise ForbiddenError("No tienes permiso para asignar prospectos.")
        new_owner_id = self.repo.get_user_id(request.owner_id)
        if new_owner_id is None:
            raise NotFoundError("El usuario responsable no existe.")
        if new_owner_id == prospect.owner_id:
            return ProspectRead.model_validate(prospect)

        old_owner_id = prospect.owner_id
        prospect.owner_id = new_owner_id
        self.repo.s.refresh(prospect, attribute_names=["owner"])
        self.repo.add_assignment(
            ProspectAssignment(
                prospect_id=prospect.id,
                from_user_id=old_owner_id,
                to_user_id=new_owner_id,
                assigned_by_id=actor.id,
                reason=request.reason or "Reasignación",
            )
        )
        if self.audit:
            self.audit.record(
                "prospect.assigned",
                "prospect",
                prospect.public_id,
                label=prospect.display_name,
                after={"owner_id": str(request.owner_id), "reason": request.reason},
            )
        return ProspectRead.model_validate(prospect)

    def bulk_assign(self, request: BulkAssignRequest, actor: User) -> dict:
        if P.PROSPECTS_ASSIGN not in actor.permission_codes:
            raise ForbiddenError("No tienes permiso para asignar prospectos.")
        new_owner_id = self.repo.get_user_id(request.owner_id)
        if new_owner_id is None:
            raise NotFoundError("El usuario responsable no existe.")
        updated = 0
        for pid in request.prospect_ids:
            try:
                self.assign_prospect(pid, AssignRequest(owner_id=request.owner_id, reason=request.reason), actor)
                updated += 1
            except NotFoundError:
                pass
        return {"updated": updated}

    def change_status(self, public_id: UUID, request: StatusChangeRequest, actor: User) -> ProspectRead:
        prospect = self._prospect(public_id)
        if (
            P.PROSPECTS_UPDATE_ALL not in actor.permission_codes
            and prospect.owner_id != actor.id
        ):
            raise ForbiddenError("No puedes cambiar el estado de este prospecto.")
        if request.status.value == prospect.status:
            return ProspectRead.model_validate(prospect)

        old_status = prospect.status
        prospect.status = request.status.value
        self.repo.add_status_history(
            ProspectStatusHistory(
                prospect_id=prospect.id,
                from_relationship_type=prospect.relationship_type,
                to_relationship_type=prospect.relationship_type,
                from_status=old_status,
                to_status=prospect.status,
                changed_by_id=actor.id,
                reason=request.reason,
            )
        )
        self.repo.add_prospect(prospect)
        if self.audit:
            self.audit.record(
                "prospect.status_changed",
                "prospect",
                prospect.public_id,
                label=prospect.display_name,
                before={"status": old_status},
                after={"status": prospect.status},
            )
        return ProspectRead.model_validate(prospect)


from app.modules.prospects.infrastructure.models import ProspectContact  # noqa: E402
from app.modules.rbac.domain.permissions import P  # noqa: E402
