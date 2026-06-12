# mm-fastapi

FastAPI 插件，用于集成 MetaMessage 协议。支持二进制（MetaMessage Binary）和 JSONC 两种数据格式的自动切换。

## 特性

- **自动编解码** - 根据请求 `Content-Type` 自动选择二进制或 JSONC 格式
- **中间件支持** - `MMMiddleware` 全局编解码中间件，透明处理所有请求/响应
- **依赖注入** - 提供 `MM`、`MMBody` 依赖注入，自动解析请求体
- **数据绑定** - `bind_body` / `bind_and_validate` 绑定请求体到 Pydantic 模型
- **自定义验证** - `mm_validate` 支持模型的 `validate()` 方法
- **装饰器支持** - 使用 `@mm_route` 装饰器简化路由定义
- **MMRouter** - 扩展的 APIRouter，自动处理 MetaMessage 编码
- **Schema 发现** - `mm_options_handler` 支持 OPTIONS 请求返回请求结构
- **客户端 SDK** - `MMClient` / `AsyncMMClient` 完整的同步/异步 HTTP 客户端
- **错误处理** - `mm_error` / `mm_respond` 便捷的 MetaMessage 格式响应函数

## 安装

```bash
pip install fastapi-mm
```

## 快速开始

### 服务端

```python
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi_mm import MMMiddleware, MM, mm_route, mm_respond, mm_error, mm_options_handler

app = FastAPI()
app.add_middleware(MMMiddleware)


class CreateUserRequest(BaseModel):
    name: str = Field(..., description="User name", min_length=1, max_length=50)
    email: str = Field(..., description="User email")
    age: int = Field(..., description="User age", ge=0, le=150)


class User(CreateUserRequest):
    id: int = 0
    is_active: bool = True


users_db = []


@app.get("/health")
async def health():
    return mm_respond({"status": "ok"})


@app.post("/users")
async def create_user(user: MM[CreateUserRequest]):
    new_user = User(id=len(users_db) + 1, **user.data.model_dump())
    users_db.append(new_user)
    return mm_respond({"code": 0, "message": "created", "data": new_user.model_dump()}, status_code=201)


@app.options("/users")
async def options_users():
    return mm_options_handler(CreateUserRequest(name="Example", email="ex@ample.com", age=0))
```

### 客户端

```python
from fastapi_mm import MMClient

# 使用上下文管理器
with MMClient("http://localhost:8000") as client:
    # 健康检查
    status = client.health()
    print(status)

    # 创建用户
    resp = client.post("/users", {"name": "Alice", "email": "alice@example.com", "age": 30})
    print(resp.data)

    # 获取用户列表
    resp = client.get("/api/v1/users")
    print(resp.data)

    # Schema 发现
    schema = client.options("/users")
    print(schema)
```

## Content-Type

| Content-Type                | 说明                           |
| --------------------------- | ------------------------------ |
| `application/x-metamessage` | MetaMessage 二进制格式（默认） |
| `application/jsonc`         | JSONC 格式（支持注释的 JSON）  |

## API 参考

### 中间件

#### MMMiddleware

全局中间件，自动处理请求/响应的编解码。

```python
from fastapi_mm import MMMiddleware

app = FastAPI()
app.add_middleware(MMMiddleware)
```

### 依赖注入

#### MM[T]

依赖注入类，用于自动解析请求体。

```python
@app.post("/users")
async def create_user(user: MM[User]):
    return user.data
```

#### MMBody

创建绑定到模型的依赖。

```python
@app.post("/users")
async def create_user(user: User = MMBody(User)):
    return user
```

### 工具函数

#### mm_respond(data, status_code=200, format=MMFormat.BINARY)

创建 MetaMessage 格式的响应。类似 mm-gin 的 `Respond()`。

```python
@app.get("/users")
async def list_users():
    return mm_respond({"users": [...]})
```

#### mm_error(message, status_code=400)

创建 MetaMessage 格式的错误响应。类似 mm-gin 的 `AbortWithMetaMessage()`。

```python
@app.get("/users/{id}")
async def get_user(id: int):
    if not user:
        return mm_error("user not found", 404)
```

#### mm_options_handler(model_instance)

创建 OPTIONS 响应用于 Schema 发现。类似 mm-gin 的 `OptionsHandler()`。

返回 MetaMessage 编码的模型结构，客户端可获取请求格式、类型、约束和描述。

```python
@app.options("/users")
async def options_users():
    return mm_options_handler(CreateUserRequest(name="", email="", age=0))
```

#### bind_body(request, model_class)

将请求体绑定到 Pydantic 模型。类似 mm-gin 的 `Bind()`。

```python
@app.post("/users")
async def create_user(request: Request):
    user = bind_body(request, CreateUserRequest)
    return mm_respond({"created": user.name})
```

#### bind_and_validate(request, model_class)

绑定并验证请求体。类似 mm-gin 的 `BindAndValidate()`。

```python
@app.post("/users")
async def create_user(request: Request):
    user = bind_and_validate(request, CreateUserRequest)
    return mm_respond({"created": user.name})
```

#### mm_validate(obj)

自定义验证。类似 mm-gin 的 `Validate()`。

```python
class CreateUserRequest(BaseModel):
    name: str
    age: int

    def validate(self):
        if self.age < 18:
            return "User must be 18 or older"
        return None

user = CreateUserRequest(name="Alice", age=16)
error = mm_validate(user)  # "User must be 18 or older"
```

### 客户端 SDK

#### MMClient

同步 HTTP 客户端。

```python
from fastapi_mm import MMClient

client = MMClient("http://localhost:8000")

# 支持上下文管理器
with MMClient("http://localhost:8000") as client:
    resp = client.get("/users")
    print(resp.data)
    print(resp.status_code)

# 设置超时
client = MMClient("http://localhost:8000", timeout=30.0)

# JSONC 格式
from fastapi_mm import MMFormat
client = MMClient("http://localhost:8000", default_format=MMFormat.JSONC)
```

#### AsyncMMClient

异步 HTTP 客户端。

```python
from fastapi_mm import AsyncMMClient

async with AsyncMMClient("http://localhost:8000") as client:
    resp = await client.post("/users", {"name": "Alice", "age": 30})
    print(resp.data)
```

#### MMClient 方法

| 方法                | 说明                   |
| ------------------- | ---------------------- |
| `get(path)`         | GET 请求               |
| `post(path, body)`  | POST 请求              |
| `put(path, body)`   | PUT 请求               |
| `patch(path, body)` | PATCH 请求             |
| `delete(path)`      | DELETE 请求            |
| `options(path)`     | Schema 发现 (OPTIONS)  |
| `health()`          | 健康检查 (GET /health) |
| `close()`           | 关闭客户端             |

### 装饰器

#### mm_route

路由装饰器，提供编解码支持。

```python
@mm_route.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"id": item_id, "name": "Example"}
```

### 编解码函数

```python
from fastapi_mm import encode, decode, encode_jsonc, decode_jsonc

data = encode({"name": "Alice", "age": 30})
obj = decode(data)
jsonc = encode_jsonc({"name": "Alice", "age": 30})
obj = decode_jsonc(jsonc)
```

### 配置选项

```python
from fastapi_mm import MMConfig, MMFormat

config = MMConfig(
    default_format=MMFormat.BINARY,
    auto_detect=True,
    pretty_jsonc=True,
    validate_input=True,
)

app.add_middleware(MMMiddleware, config=config)
```

## 示例

### 完整 CRUD 示例

本项目提供了完整的服务端 + 客户端示例，展示 MetaMessage 协议的完整 CRUD 流程。

```bash
# 1. 启动服务端
cd examples
python server_example.py

# 2. 新开终端，运行客户端测试
python client_example.py
```

服务端提供以下端点：

| 方法    | 路径                | 说明                            |
| ------- | ------------------- | ------------------------------- |
| GET     | /health             | 健康检查                        |
| GET     | /api/v1/users       | 获取用户列表                    |
| GET     | /api/v1/users/{id}  | 获取单个用户                    |
| POST    | /api/v1/users       | 创建用户（二进制格式）          |
| PUT     | /api/v1/users/{id}  | 更新用户（二进制格式）          |
| DELETE  | /api/v1/users/{id}  | 删除用户                        |
| OPTIONS | /api/v1/users       | Schema 发现（创建用户请求结构） |
| OPTIONS | /api/v1/users/{id}  | Schema 发现（更新用户请求结构） |
| POST    | /api/v1/jsonc/users | 创建用户（JSONC 格式）          |

### 使用 curl 测试

```bash
# 健康检查
curl http://localhost:8000/health

# 获取用户列表（MetaMessage 二进制）
curl -H "Accept: application/x-metamessage" http://localhost:8000/api/v1/users

# 创建用户（MetaMessage 二进制）
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/x-metamessage" \
  -H "Accept: application/x-metamessage" \
  -d '{"name":"David","email":"david@example.com","age":28}'

# 更新用户
curl -X PUT http://localhost:8000/api/v1/users/1 \
  -H "Content-Type: application/x-metamessage" \
  -H "Accept: application/x-metamessage" \
  -d '{"name":"Alice Updated"}'

# Schema 发现
curl -X OPTIONS http://localhost:8000/api/v1/users
```

### 其他示例文件

| 文件                           | 说明                                   |
| ------------------------------ | -------------------------------------- |
| `examples/server_example.py`   | 完整 CRUD 服务端（MetaMessage 二进制） |
| `examples/client_example.py`   | 独立客户端测试（使用 MMClient SDK）    |
| `examples/basic_example.py`    | 基础用法（中间件、依赖注入、装饰器）   |
| `examples/advanced_example.py` | 高级用法（电商 API，完整功能演示）     |

## 测试

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_fastapi_mm.py -v

# 带覆盖率
pytest tests/ -v --cov=fastapi_mm --cov-report=term-missing
```

### 测试内容

| 测试类           | 测试内容                                   |
| ---------------- | ------------------------------------------ |
| TestCodec        | encode/decode 编解码，JSONC 转换，往返测试 |
| TestMiddleware   | JSON/JSONC 请求处理，OpenAPI 路由跳过      |
| TestDependencies | MM 依赖注入，MMBody 依赖                   |
| TestDecorators   | mm_route 装饰器，MMRouter                  |
| TestTypes        | MMFormat 检测，MMConfig 默认值             |
| TestOpenAPI      | OpenAPI 集成，Schema 生成                  |
| TestIntegration  | 完整工作流，错误处理                       |

## 依赖

- [FastAPI](https://github.com/tiangolo/fastapi) - Web 框架
- [MetaMessage](https://github.com/metamessage/metamessage) - MetaMessage 协议 Python 实现
- [Pydantic](https://github.com/pydantic/pydantic) - 数据验证
- [httpx](https://github.com/encode/httpx) - HTTP 客户端（客户端 SDK）

## 许可证

MIT License
