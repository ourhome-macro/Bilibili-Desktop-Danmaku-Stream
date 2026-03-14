from typing import Any, Optional
from flask import jsonify, Response


class Result:
    def __init__(self, success: bool, data: Optional[Any] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> dict:
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result

    def json(self) -> Response:
        return jsonify(self.to_dict())

    def json_with_status(self, status_code: int = 200) -> tuple[Response, int]:
        return jsonify(self.to_dict()), status_code

    @classmethod
    def ok(cls, data: Any = None) -> "Result":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str, data: Optional[Any] = None) -> "Result":
        return cls(success=False, error=error, data=data)

    @classmethod
    def bad_request(cls, error: str) -> tuple[Response, int]:
        return cls(success=False, error=error).json_with_status(400)

    @classmethod
    def server_error(cls, error: str) -> tuple[Response, int]:
        return cls(success=False, error=error).json_with_status(500)
