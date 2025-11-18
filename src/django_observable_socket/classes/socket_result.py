from typing_extensions import TypedDict, Optional, Any

from .message import Header


class SocketResult(TypedDict, total=False):
    headers: Optional[Header]
    payload: Optional[Any]
    status: Optional[int]
