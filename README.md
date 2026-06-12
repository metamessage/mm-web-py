# mm-web-py

MetaMessage protocol integrations for Python web frameworks.

This monorepo provides three packages:

- **[mm-core](src/mm_core/)** - Shared types, errors, and HTTP client SDK (framework-agnostic)
- **[mm-fastapi](src/mm_fastapi/)** - FastAPI integration with `MMRouter`, `MMMiddleware`, and route decorators
- **[mm-flask](src/mm_flask/)** - Flask integration with `MMFlask`, `MMMiddleware`, and route decorators

## What is MetaMessage?

[MetaMessage](https://github.com/metamessage/metamessage) is a binary serialization protocol that provides efficient encoding/decoding of structured data. It follows the convention:

- **GET/DELETE** requests: Parameters are hex-encoded as `?data=<hex>` query parameter
- **POST/PUT/PATCH** requests: Body is binary MetaMessage
- **Responses**: Always binary MetaMessage

## Packages

### mm-core

Shared framework-agnostic code:

- `CONTENT_TYPE_METAMESSAGE` - Content type constant (`application/metamessage`)
- `MMEncoderError` / `MMDecoderError` - Encoding/decoding error classes
- `MMClient` / `AsyncMMClient` - Synchronous and asynchronous HTTP clients

### mm-fastapi

```python
from fastapi import FastAPI
from mm_fastapi import MMRouter

app = FastAPI()
router = MMRouter(app)

@router.get("/users")
async def list_users(req: User) -> User:
    return User(name=req.name, age=req.age)

@router.post("/users")
async def create_user(req: User) -> User:
    return User(name=req.name, age=req.age)
```

### mm-flask

```python
from flask import Flask
from mm_flask import MMFlask, MMMiddleware

app = Flask(__name__)
MMMiddleware(app)
mm = MMFlask(app)

@mm.get("/users")
def list_users(req: User) -> User:
    return User(name=req.name, age=req.age)

@mm.post("/users")
def create_user(req: User) -> User:
    return User(name=req.name, age=req.age)
```

## Installation

### Install all packages

```bash
pip install -e ".[dev]"
```

### Install specific framework extras

```bash
# FastAPI
pip install -e ".[fastapi]"

# Flask
pip install -e ".[flask]"
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Project Structure

```
src/
├── mm_core/           # Shared types, errors, client SDK
├── mm_fastapi/        # FastAPI integration
└── mm_flask/          # Flask integration
tests/
├── mm-fastapi/        # FastAPI tests
└── mm-flask/          # Flask tests
examples/
├── mm-fastapi/        # FastAPI examples
└── mm-flask/          # Flask examples
```

## License

MIT License