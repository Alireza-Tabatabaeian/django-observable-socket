# Django Channels Router (Backend, PyPI)

A lightweight Django + Channels router that lets your WebSocket consumers behave like HTTP endpoints.  
Designed to pair seamlessly with [`@djanext/observable-socket`](https://www.npmjs.com/package/@djanext/observable-socket).

---

## Features
- 🧭 Route names → handler methods (`sayHello` → `on_say_hello`)
- ⚡  Both sync & async consumers
- 🧩 Optional `hydrate` / `dehydrate` functions
- 🔁 Built-in heartbeat support (`PING`/`PONG`)
- 📦 Typed results and HTTP-style status codes

---

## Requirements
- **Python** ≥ 3.11  
- **Django** ≥ 4.2  
- **Channels** ≥ 4.0  
- **Redis** (or any supported channel layer)

---

## Installation

```bash
pip install django-channels-router
```

In your project:
```py
# routing.py
from django.urls import re_path
from .consumer import AppSocket

websocket_urlpatterns = [
    re_path(r"ws/app/$", AppSocket.as_asgi()),
]
```

---

## Example Consumer

```py
from django_channels_router import SocketRouterConsumer, StatusCodes



def can_load_article(scope, fetched_data):

class AppSocket(SocketRouterConsumer):
    @SocketRouterConsumer.routes.setter
    def routes(self, _):
        self._routes = [
            {"route": "sayHello"},
            {"route": "getArticle",
             ""
             "hydrate": lambda headers, p: load_article(p["id"]),
             "dehydrate": lambda art: {"id": art.id, "title": art.title}
             },
        ]

    def on_say_hello(self, payload, headers):
        name = (payload or {}).get("name", "World")
        return {"status": StatusCodes.OK, "payload": f"Hello, {name}!"}
```

**Async Example**
```py
from django_channels_router import AsyncSocketRouterConsumer

class AppSocketAsync(AsyncSocketRouterConsumer):
    @AsyncSocketRouterConsumer.routes.setter
    def routes(self, _):
        self._routes = [{"route": "sayHello"}]

    async def on_say_hello(self, payload, headers):
        return {"status": 200, "payload": {"msg": "Hello async!"}}
```

---

## Serializing and Deserializing of messages

**hydrate** and **dehydrate** functions helps to focus only on logic part as these functions will handle deserializing and serializing automatically.
To use them, first you need to implement the converters (loader, serializer, ...)

```py
def load_article(headers, payload) -> Article | None:
    try:
        article_id = headers.get('id')
        if not article_id:
            return None
        return Article.objects.get(id=article_id) # assume id is of type string like uuid
    except Article.DoesNotExist:
        return None

def deserialize(headers, payload) -> Article | None:
    try:
        serializer = ArticleSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return serializer.save()
    except serializers.ValidationError:
        return None

def serialize(article: Article) -> str:
    serializer = ArticleSerializer(article)
    return serializer.data
```

now these converters can be used as follows:

```python
    class ArticleConsumer(SocketRouterConsumer):
        routes = [
            {route: get, hydrate: load_article, dehydrate: serialize},
            {route: create, hydrate: deserialize, dehydrate: serialize}
        ]
        
        def on_get(headers, payload):
            return {
                payload: payload, 
                # article gets fetched from DB in background using the `load_article` function
                # dehydrate will automatically serilize the article by running `serialize` function
                status: StatusCodes.OK if payload else StatusCodes.NOT_FOUND 
            }
            
        def on_create(headers, payload):
            if not payload: # deserialize function has returned None
                return {
                    payload: "Unable to create article",
                    status: StatusCodes.BAD_REQUEST
                }
                
            return {
                payload: payload,
                status: StatusCodes.CREATED
            }
```

#### Note:
**dehydrate** function only applies if returned status code by user is 200 series. (199 < status code < 300) 

---

## Status Codes

| Symbol | Value | Meaning |
|---------|--------|---------|
| `StatusCodes.OK` | 200 | Success |
| `StatusCodes.BAD_REQUEST` | 400 | Malformed message |
| `StatusCodes.NOT_FOUND` | 404 | Unknown route |
| `StatusCodes.INTERNAL_SERVER_ERROR` | 500 | Handler failure |

---

## Good Practices
- Always `accept()` connections in `connect()` / `await accept()`.
- Access `result.get("payload")` safely — avoid missing keys.
- Use `@classmethod` route definitions if you plan to reuse the router base.
- Keep payload JSON-serializable.

---

## Frontend Client

Pair with `@djanext/observable-socket`  
→ Handles auto-reconnect, multiple sockets, and `sendAndWait()` with Promises.

---

## License

MIT