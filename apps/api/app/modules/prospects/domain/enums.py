from enum import StrEnum


class PersonType(StrEnum):
    NATURAL = "NATURAL"
    JURIDICA = "JURIDICA"


class RelationshipType(StrEnum):
    PROSPECTO = "PROSPECTO"
    CLIENTE = "CLIENTE"


class ProspectStatus(StrEnum):
    ACTIVO = "ACTIVO"
    EN_PAUSA = "EN_PAUSA"
    DESCARTADO = "DESCARTADO"
    NO_CALIFICA = "NO_CALIFICA"
    INACTIVO = "INACTIVO"
