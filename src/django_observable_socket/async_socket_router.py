from typing_extensions import Callable, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from pydantic import ValidationError

from .classes import AuxiliaryStore, SocketResult, AbstractSocketRouter, BaseMessage, RouteInfo, StatusCodes, \
    HydratedMessageData, RequestMessage, ResponseMessage, set_error, CallError, GenericRouteInfo, FetchedData
from .tools import route_to_method_name, result_is_successful

MainHandler = Callable[[HydratedMessageData, Optional[AuxiliaryStore]], SocketResult]

User = settings.AUTH_USER_MODEL


class AsyncSocketRouterConsumer(AsyncJsonWebsocketConsumer, AbstractSocketRouter):
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

    _user = None

    @property
    def user(self) -> User:
        return self._user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connect(self):
        self._user = self.scope['user']
        self.accept()

    async def receive_json(self, content, **kwargs):
        try:
            message = RequestMessage(**content)
            if message.route == 'PING':  # only heart-bit checks, response, so the client makes sure the connection is open
                await self.send_json(
                    BaseMessage(
                        route='PONG',
                        uuid=message.uuid
                    ).model_dump()
                )
                return

            # find route
            route_info: GenericRouteInfo | None = self._get_route(message.route)
            if not route_info:
                await self.send_json(
                    message.respond(headers=None, payload=set_error(CallError.RouteNotFound),
                                    status=StatusCodes.NOT_FOUND)
                )
                return

            # find method
            method_name = route_to_method_name(route_info.route)
            try:
                method = getattr(self, method_name)  # if the method doesn't exist, an exception will be raised
            except AttributeError:
                await self.send_json(
                    message.respond(headers=None, payload=set_error(CallError.MethodNotImplemented),
                                    status=StatusCodes.INTERNAL_SERVER_ERROR)
                )
                return

            auxiliary_payload = dict()

            fetched_data: FetchedData = message.fetch_data()

            check_data = route_info.check_data
            if check_data:
                data_check = await check_data(fetched_data, auxiliary_payload)
                if not data_check:
                    await self.send_json(
                        message.respond(
                            payload=set_error(CallError.InvalidData),
                            status=StatusCodes.BAD_REQUEST
                        )
                    )
                    return

            check_access = route_info.check_access
            if check_access:
                access_checked = await check_access(self.scope, fetched_data, auxiliary_payload)
                if not access_checked:
                    await self.send_json(
                        message.respond(
                            payload=set_error(CallError.AccessDenied),
                            status=StatusCodes.FORBIDDEN
                        )
                    )
                return

            # hydrate the payload if the function is provided
            hydrate = route_info.hydrate
            if hydrate:
                hydrated_payload = await hydrate(fetched_data)
                handler_params: HydratedMessageData = {
                    'headers': message.headers,
                    'payload': hydrated_payload
                }
                result: SocketResult = await method(handler_params, auxiliary_payload)
            else:
                result = await method(fetched_data, auxiliary_payload)

            dehydrate = route_info.dehydrate
            should_dehydrate: bool = dehydrate and result_is_successful(result.get('status', StatusCodes.OK))
            out_payload = await dehydrate(result['payload']) if should_dehydrate else result['payload']

            await self.send_json(
                message.respond(
                    headers=result.get('headers'),
                    payload=out_payload,
                    status=result.get('status', StatusCodes.OK)
                )
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
