import inspect
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from pydantic import ValidationError

from .classes import BaseRouter, StatusCodes, RequestMessage, ResponseMessage, set_error, CallError, \
    GenericRouteInfo, enforce_routes
from .classes.types import HandlerArg, SocketResult
from .tools import route_to_method_name, result_is_successful

logger = logging.getLogger(__name__)

class AsyncSocketRouterConsumer(AsyncJsonWebsocketConsumer, BaseRouter):
    from django.conf import settings
    User = settings.AUTH_USER_MODEL
    """
    To implement this class, you'll need to assign _routes attribute for it:

    this attribute can simply be assigned with a list or tuple of RouteInfo objects like this:
        _routes = [
            {'route': 'sayHello'}, # only required property of `RouteInfo` is `route`
            {'route': 'postArticle', 'check_data': article_validator, 'check_access': can_post_article'}, # data check and operation access will be checked automatically
            GenericRouteInfo[Article,Article](route ='getArticle', hydrate=load_article, dehydrate=article_serializer) # using GenericRouteInfo, return type of hydrate function and input type of dehydrate function can be defined
        ]

        or

        _routes = (
        {'route': 'sayHello'}, # only required property of `RouteInfo` is `route`
        )

    if set as list, the attribute then will be converted to tuple automatically at class initiation runtime, in order to prevent mutation.

    Then, if you have a route like `sayHello`,
    your consumer will need to have a method named on_say_hello, and there you can define the code you expect to be executed when sayHello is called.

    So when in the frontend you call sayHello route, the code in on_say_hello will be executed automatically.

    Read more in README.md about how it facilitates the entire process, using check_data, check_access, hydrate ,and dehydrate functions.
    """

    def __init_subclass__(cls, **kwargs):
        if cls is not AsyncSocketRouterConsumer:
            enforce_routes(cls)

    _user = None

    @property
    def user(self) -> User:
        return self._user

    async def connect(self):
        self._user = self.scope['user'] if self._user is None else self._user
        await self.accept()

    async def receive_json(self, content, **kwargs):
        try:
            message = RequestMessage(**content)
            if message.route == 'PING':  # only heart-bit checks, response, so the client makes sure the connection is open
                await self.send_json(
                    RequestMessage(
                        route='PONG',
                        uuid=message.uuid
                    ).model_dump()
                )
                return

            # find route
            route_info: GenericRouteInfo | None = self._get_route(message.route)
            if not route_info:
                await self.send_json(
                    message.error(error=set_error(CallError.RouteNotFound), status=StatusCodes.NOT_FOUND)
                )
                return

            # find method
            method_name = route_to_method_name(route_info.route)
            try:
                main_handler = getattr(self, method_name)  # if the method doesn't exist, an exception will be raised
            except AttributeError:
                await self.send_json(
                    message.error(status=StatusCodes.INTERNAL_SERVER_ERROR,
                                  error=set_error(CallError.MethodNotImplemented))
                )
                return

            try: # Handling any issues in user code
                inner_data = HandlerArg(scope=self.scope, headers=message.headers, payload=message.payload, store=dict())

                # check input data if such method is provided
                check_data = route_info.check_data
                if check_data:
                    is_awaitable = inspect.iscoroutinefunction(check_data)
                    data_check = await check_data(inner_data) if is_awaitable else check_data(inner_data)
                    if not data_check:
                        await self.send_json(
                            message.error(status=StatusCodes.BAD_REQUEST, error=set_error(CallError.InvalidData))
                        )
                        return

                # check access permission if such method is provided
                check_access = route_info.check_access
                if check_access:
                    is_awaitable = inspect.iscoroutinefunction(check_access)
                    access_checked = await check_access(inner_data) if is_awaitable else check_access(inner_data)
                    if not access_checked:
                        await self.send_json(
                            message.error(error=set_error(CallError.AccessDenied), status=StatusCodes.FORBIDDEN)
                        )
                    return

                # hydrate the payload if the function is provided
                hydrate = route_info.hydrate
                if hydrate:
                    is_awaitable = inspect.iscoroutinefunction(hydrate)
                    inner_data.payload = await hydrate(inner_data) if is_awaitable else hydrate(inner_data)

                # run main handler
                is_awaitable = inspect.iscoroutinefunction(main_handler)
                result: SocketResult = await main_handler(inner_data) if is_awaitable else main_handler(inner_data)

                # dehydrate if dehydrate is provided and main handler has returned 2xx status
                dehydrate = route_info.dehydrate
                should_dehydrate: bool = dehydrate and result_is_successful(result.get('status', StatusCodes.OK))
                if should_dehydrate:
                    is_awaitable = inspect.iscoroutinefunction(dehydrate)
                    result['payload'] = await dehydrate(result.get('payload')) if is_awaitable else dehydrate(result.get('payload'))

                # return final result
                await self.send_json(message.respond(result))

            except Exception as e:
                logger.error(str(e))
                await self.send_json(
                    message.error(status=StatusCodes.INTERNAL_SERVER_ERROR,
                                  error=set_error(CallError.InternalServerError))
                )
        except ValidationError:
            response = {
                'uuid': content.get('uuid', ''),
                'status': StatusCodes.BAD_REQUEST,
                'payload': set_error(CallError.BadRequestFormat)
            }
            await self.send_json(
                ResponseMessage(**response).model_dump()
            )