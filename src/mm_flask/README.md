# mm-flask

Flask integration for the MetaMessage protocol. Provides automatic MetaMessage encoding/decoding for Flask applications.

## Features

- **Automatic encoding/decoding** - MetaMessage binary format for requests and responses
- **Middleware** - `MMMiddleware` handles request decoding and response encoding
- **Route decorators** - `MMFlask` class with `.get()`, `.post()`, `.put()`, `.delete()`, `.patch()` decorators
- **Parameter binding** - GET/DELETE from `?data=<hex>` query, POST/PUT/PATCH from binary body
- **Utility functions** - `mm_respond()`, `mm_error()`, `mm_body()`, `bind_body()`

## Installation

```bash
pip install mm-flask
```

## Quick Start

```python
from dataclasses import dataclass
from flask import Flask
from metamessage import mm
from mm_flask import MMFlask, MMMiddleware


@mm(desc="User request")
@dataclass
class User:
    name: str
    age: int
    email: str


app = Flask(__name__)
MMMiddleware(app)
mm = MMFlask(app)


@mm.post("/users")
def create_user(req: User) -> dict:
    return {"id": 1, "name": req.name, "age": req.age}


@mm.get("/users/<int:user_id>")
def get_user(user_id: int, req: User) -> dict:
    return {"id": user_id, "name": req.name, "age": req.age}


@mm.delete("/users/<int:user_id>")
def delete_user(user_id: int) -> dict:
    return {"id": user_id, "deleted": True}


if __name__ == "__main__":
    app.run()
```

## Testing with curl

```bash
# POST with binary MetaMessage
curl -X POST http://localhost:5000/users \
  -H "Content-Type: application/metamessage" \
  -H "Accept: application/metamessage" \
  --data-binary @<(python -c "from metamessage import encode_from_value; import sys; sys.stdout.buffer.write(encode_from_value({'name': 'Alice', 'age': 30, 'email': 'a@b.com'}))")

# GET with hex-encoded MetaMessage
python -c "
from metamessage import encode_from_value
import urllib.request
raw = encode_from_value({'name': 'Alice', 'age': 30, 'email': 'a@b.com'})
import subprocess; subprocess.run(['curl', f'http://localhost:5000/users/42?data={raw.hex()}'])
"
```

## API Reference

### MMMiddleware

```python
from mm_flask import MMMiddleware

app = Flask(__name__)
MMMiddleware(app)
```

### MMFlask

```python
from mm_flask import MMFlask

mm = MMFlask(app)

@mm.get("/path")
def handler(req: Model):
    return result
```

### Utility Functions

- `mm_respond(data, status_code=200)` - Create MetaMessage-encoded response
- `mm_error(message, status_code=400)` - Create error response
- `mm_body()` - Get decoded body from request
- `bind_body(Model)` - Bind request body to model

## Dependencies

- [Flask](https://github.com/pallets/flask) >= 2.0.0
- [MetaMessage](https://github.com/metamessage/metamessage) - MetaMessage protocol Python implementation
- [mm-core](https://github.com/metamessage/mm-web-py) - Shared MetaMessage types (included)

## License

MIT License