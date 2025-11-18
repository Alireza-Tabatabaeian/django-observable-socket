from abc import ABC
from typing import Tuple

from typing_extensions import TypedDict, Generic, ClassVar

from .message import Header
from .route_info import RouteInfo, HydratedPayload, is_route_info, GenericRouteInfo


class HydratedMessageData(TypedDict, Generic[HydratedPayload]):
    headers: Header
    payload: HydratedPayload


class AbstractSocketRouter(ABC):
    _routes: ClassVar[Tuple[GenericRouteInfo, ...]] = ()

    @classmethod
    def routes(cls) -> Tuple[GenericRouteInfo, ...]:
        """Class-level accessor returning an immutable tuple of routes."""
        return cls._routes

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # skip enforcement for the base class itself
        if cls is AbstractSocketRouter or cls.__name__ in ['SocketRouterConsumer', 'AsyncSocketRouterConsumer']:
            return

        if not hasattr(cls, "_routes"):
            raise TypeError(f"{cls.__name__} must define a `_routes` class attribute")

        routes = getattr(cls, "_routes")

        if isinstance(routes, tuple):
            routes = list(routes)

        if not isinstance(routes, list):
            raise TypeError(f"{cls.__name__}._routes must be a tuple or list (got {type(routes).__name__})")

        for i, route_info in enumerate(routes):
            if not is_route_info(route_info):
                raise TypeError(f"{cls.__name__}._routes[{i}] looks invalid: {route_info!r}")
            if not isinstance(route_info, GenericRouteInfo):
                routes[i] = GenericRouteInfo(**route_info)

        cls._routes = tuple(routes)

    @classmethod
    def _get_route(cls, path: str) -> GenericRouteInfo | None:
        for i, route_info in enumerate(cls.routes()):
            if route_info.route == path:
                return route_info
        return None
