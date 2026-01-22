from enum import Enum
from typing import Dict

Error = Dict[str, str]


class CallError(str, Enum):
    InvalidData = "Invalid Data"
    AccessDenied = "Access Denied"
    RouteNotFound = "Route Not Found"
    MethodNotImplemented = "Method Not Implemented"
    BadRequestFormat = "Request Format Error"
    InternalServerError = "Internal Server Error"


def set_error(error: CallError) -> Error:
    return {'error': str(error)}
