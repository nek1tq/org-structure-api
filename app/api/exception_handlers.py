from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ConflictError, NotFoundError, ValidationError


async def _not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def _validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found_handler)
    app.add_exception_handler(ConflictError, _conflict_handler)
    app.add_exception_handler(ValidationError, _validation_handler)
