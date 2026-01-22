from typing import Dict, Union, List, Any, Generic, Callable, Awaitable, Optional, TypedDict

from pydantic import JsonValue, BaseModel, ConfigDict
from typing_extensions import TypeVar

Header = Dict[str, JsonValue] | None
JSON = Union[
    None,
    bool,
    int,
    float,
    str,
    List["JSON"],
    Dict[str, "JSON"],
]

AuxiliaryStore = Dict[str, Any]
HydratedPayload = TypeVar('HydratedPayload')
HandlerPayload = TypeVar('HandlerPayload')
Scope = TypeVar('Scope', bound=Dict)


class HandlerArg(BaseModel, Generic[Scope, HydratedPayload]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scope: Scope
    headers: Header
    payload: Union[JsonValue | HydratedPayload]
    store: AuxiliaryStore


CheckMethod = Callable[[HandlerArg], bool] | Callable[[HandlerArg], Awaitable[bool]]

HydrateMethod = Callable[[HandlerArg], HydratedPayload] | Callable[[HandlerArg], Awaitable[HydratedPayload]]


class SocketResult(TypedDict, Generic[HandlerPayload]):
    headers: Optional[Header]
    payload: Optional[HandlerPayload]
    status: Optional[int]


HandlerMethod = Callable[[HandlerArg], SocketResult] | Callable[[HandlerArg], Awaitable[SocketResult]]

DeHydrateMethod = Callable[[HandlerPayload], JsonValue] | Callable[[HandlerPayload], Awaitable[JsonValue]]