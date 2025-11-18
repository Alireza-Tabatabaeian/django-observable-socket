from pydantic import BaseModel, ValidationError
from typing_extensions import Union, List, Dict, Optional, TypedDict

from .status import StatusCodes

JSON = Union[
    None,
    bool,
    int,
    float,
    str,
    List["JSON"],
    Dict[str, "JSON"],
]

Header = Dict[str, JSON] | None

class FetchedData(TypedDict):
    headers: Header
    payload: JSON

class MessageData(BaseModel):
    headers: Optional[Header]
    """
        While there aren't actual headers per socket message when using it as transition protocol, to make it feel more like http call
        this field is added, I found it meaningful to send metadata(like API_KEY or even entity ID) through headers and use payload to send actual data 
    """

    payload: Optional[JSON]
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
    route: str
    """
        route is used to determine which method is responsible to handle the incoming message
        the routes will convert to snakecase for making method names.
        method names will follow this: f"on_{snakecase(route)}"
    """

    def fetch_data(self) -> FetchedData:
        return {
            'headers': self.headers,
            'payload': self.payload
        }

    def respond(self, headers: Header = None, payload: JSON = None, status: int = StatusCodes.OK):
        response = {
            'uuid': self.uuid,
            'headers': headers,
            'payload': payload,
            'status': status
        }
        try:
            response_message = ResponseMessage(**response)
            return response_message.model_dump()
        except ValidationError:
            response = {
                'uuid': self.uuid,
                'headers': None,
                'payload': None,
                'status': StatusCodes.INTERNAL_SERVER_ERROR
            }
            try:
                response_message = ResponseMessage(**response)
                return response_message.model_dump()
            except ValidationError:
                return None


BaseMessage = RequestMessage | ResponseMessage
