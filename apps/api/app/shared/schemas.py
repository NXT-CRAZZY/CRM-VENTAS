from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Base de todos los DTOs de respuesta: se construyen desde objetos ORM."""

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MessageResponse(BaseModel):
    message: str
