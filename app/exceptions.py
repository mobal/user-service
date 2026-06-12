from typing import Any

from fastapi import HTTPException, status


class AlreadyExistsException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class NotFoundException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UserAlreadyExistsException(AlreadyExistsException):
    pass


class UserNotFoundException(NotFoundException):
    pass


class InvalidPaginationKeyException(BadRequestException):
    pass


class InvalidPasswordException(BadRequestException):
    pass
