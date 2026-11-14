from datetime import UTC, datetime


def convert_to_client(prospect, actor_id: int | None = None, when: datetime | None = None) -> None:
    """Pasa un prospecto a cliente y deja constancia de cuándo (cuenta en "Nuevos clientes")."""
    if prospect.relationship_type == "CLIENTE":
        if prospect.converted_at is None:
            prospect.converted_at = when or datetime.now(UTC)
        return
    prospect.relationship_type = "CLIENTE"
    prospect.converted_at = when or datetime.now(UTC)
    if actor_id is not None:
        prospect.converted_by_id = actor_id
