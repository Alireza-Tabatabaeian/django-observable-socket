from pydantic import BaseModel, TypeAdapter, ValidationError
from typing_extensions import Awaitable, Generic, Any, TypeVar, TypedDict, Callable, Optional, Dict

from message import FetchedData, JSON

AuxiliaryStore = Dict[str, Any]
HydratedPayload = TypeVar('HydratedPayload')
HandlerPayload = TypeVar('HandlerPayload')
Scope = TypeVar('Scope')

CheckData = (
        Callable[[FetchedData, Optional[AuxiliaryStore]], bool] |
        Callable[[FetchedData, Optional[AuxiliaryStore]], Awaitable[bool]]
)

CheckAccess = (
        Callable[[Scope, FetchedData, Optional[AuxiliaryStore]], bool] |
        Callable[[Scope, FetchedData, Optional[AuxiliaryStore]], Awaitable[bool]]
)

HydrateMethod = (
        Callable[[FetchedData, Optional[AuxiliaryStore]], HydratedPayload] |
        Callable[[FetchedData, Optional[AuxiliaryStore]], Awaitable[HydratedPayload]]
)

DeHydrateMethod = Callable[[HydratedPayload], JSON] | Callable[[HandlerPayload], Awaitable[JSON]]


class RouteInfoDict(TypedDict, total=False):
    route: str
    """
        if the incoming message has route attribute equal to `loadNode` then the on_load_node method will be called automatically.
        no more need to parse the message to recognize what has to be done.
    """

    check_data: Optional[CheckData]
    """
        allows to check if headers and payload to see if those contain required data and obey the data format.
        a dictionary is passed also which can be used to store calculated data
    """

    check_access: Optional[CheckAccess]
    """
        using it, one can check if requesting that route should be accessed or not.
        a good place to implement any content/operation access control logic.
        first passed parameter will be scope.
        a dictionary is passed also which can be used to store calculated data
    """

    hydrate: Optional[HydrateMethod]
    """
        any function that takes headers and payload, and loads the data from it.
        deserializing can be considered as good candidate.
        another example is to fetch the entity_id from headers and load the entity using it.
    """

    dehydrate: Optional[DeHydrateMethod]
    """
        the duty of dehydrate function is to get an object and serialize it as string or dict (no complex object included).
        PS. the dehydrate function runs only if status code is successful (200 series)
    """


class GenericRouteInfo(BaseModel, Generic[HydratedPayload,HandlerPayload]):
    route: str
    """
        if the incoming message has route attribute equal to `loadNode` then the on_load_node method will be called automatically.
        no more need to parse the message to recognize what has to be done.
    """

    check_data: Optional[CheckData]
    """
        allows to check if headers and payload to see if those contain required data and obey the data format.
        a dictionary is passed also which can be used to store calculated data
    """

    check_access: Optional[CheckAccess]
    """
        using it, one can check if requesting that route should be accessed or not.
        a good place to implement any content/operation access control logic.
        first passed parameter will be scope.
        a dictionary is passed also which can be used to store calculated data
    """

    hydrate: Optional[HydrateMethod]
    """
        any function that takes headers and payload, and loads the data from it.
        deserializing can be considered as good candidate.
        another example is to fetch the entity_id from headers and load the entity using it.
        """

    dehydrate: Optional[DeHydrateMethod]
    """
      the duty of dehydrate function is to get an object and serialize it as string or dict (no complex object included).
      PS. the dehydrate function runs only if status code is successful (200 series)
    """

RouteInfoDictValidator = TypeAdapter(RouteInfoDict)

def is_route_info(obj: Any) -> bool:
    if isinstance(obj, GenericRouteInfo):
        return True
    if not isinstance(obj, dict):
        return False
    try:
        RouteInfoDictValidator.validate_python(obj)
        return True
    except ValidationError:
        return False


RouteInfo = RouteInfoDict | GenericRouteInfo
