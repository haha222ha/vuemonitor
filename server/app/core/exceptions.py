from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.constants.error_codes import ERROR_CODES


class AppException(Exception):
    def __init__(self, code: int, message: str, detail: dict | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}


class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在", detail: dict | None = None):
        super().__init__(code=ERROR_CODES["NOT_FOUND"], message=message, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "未授权", detail: dict | None = None):
        super().__init__(code=ERROR_CODES["USER_CREDENTIALS_INVALID"], message=message, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, code: int = ERROR_CODES["GATE_FEATURE_UNAUTHORIZED"], message: str = "权限不足", detail: dict | None = None):
        super().__init__(code=code, message=message, detail=detail)


class BadRequestException(AppException):
    def __init__(self, message: str = "请求参数错误", detail: dict | None = None):
        super().__init__(code=ERROR_CODES["BAD_REQUEST"], message=message, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=400,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_handler(request: Request, exc: UnauthorizedException):
        return JSONResponse(
            status_code=401,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )
