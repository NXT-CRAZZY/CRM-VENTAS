from app.core.errors import AppError


class InteractionError(AppError):
    status_code = 400
    code = "INTERACTION_ERROR"
