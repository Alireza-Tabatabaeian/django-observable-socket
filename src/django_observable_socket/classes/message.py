from typing import Optional

from pydantic import BaseModel, ValidationError, JsonValue, ConfigDict

from .errors import Error
from .status import StatusCodes
from .types import Header, SocketResult


class MessageData(BaseModel):
    headers: Optional[Header] = None
    """
        While there aren't actual headers per socket message when using it as transition protocol, to make it feel more like http call
        this field is added, I found it meaningful to send metadata(like API_KEY or even entity ID) through headers and use payload to send actual data 
    """

    payload: Optional[JsonValue] = None
    """
        Payload field is designed to be used as main data storage. It's supposed to mostly contain a dictionary (the message
        object itself is Json coded and decoded so the rest data are not Json Coded), however any other value is possible
        like string, int, float, even a simple boolean or a huge base64 encoded string.
    """


class Envelope(MessageData):
    uuid: str | int
    """
        uuid acts as a tracking code, so that when server responses the client with this code,
        the client will identify which request does it belongs to. another essential part of this
        library.
    """


class ResponseMessage(Envelope):
    status: int = StatusCodes.OK
    """
        Status Field is supposed to be set for sending responses, just like HTTP calls.
    """


class RequestMessage(Envelope):
    model_config = ConfigDict(frozen=True)

    route: str
    """
        route is used to determine which method is responsible to handle the incoming message
        the routes will convert to snakecase for making method names.
        method names will follow this: f"on_{snakecase(route)}"
    """

    def respond(self, result: SocketResult):
        response = {
            'uuid': self.uuid, **result
        }
        try:
            return ResponseMessage(**response).model_dump()
        except ValidationError:
            try:
                return ResponseMessage(uuid=self.uuid, status=StatusCodes.INTERNAL_SERVER_ERROR).model_dump()
            except ValidationError:
                return None

    def error(self, status: int, error: Error):
        error = {
            'uuid': self.uuid,
            'status': status,
            'payload': error
        }
        try:
            return ResponseMessage(**error).model_dump()
        except ValidationError:
            try:
                return ResponseMessage(uuid=self.uuid, status=StatusCodes.INTERNAL_SERVER_ERROR).model_dump()
            except ValidationError:
                return None
