from enum import Enum

class CallError(str, Enum):
    InvalidData = "Invalid Data"
    AccessDenied = "Access Denied"
    RouteNotFound = "Route Not Found"
    MethodNotImplemented = "Method Not Implemented"
    BadRequestFormat = "Request Format Error"


def set_error(error: CallError) -> dict[str, str]:
    return {'error': str(error)}