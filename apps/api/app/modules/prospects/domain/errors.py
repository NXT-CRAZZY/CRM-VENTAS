from app.core.errors import AppError


class ProspectError(AppError):
    pass


class DuplicateDocumentError(ProspectError):
    code = "PROSPECT_DUPLICATE_DOCUMENT"
    status_code = 409


class InvalidDocumentError(ProspectError):
    code = "PROSPECT_INVALID_DOCUMENT"
    status_code = 422
