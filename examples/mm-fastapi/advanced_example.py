"""Advanced example showing all features of fastapi-mm."""

from typing import List, Optional, Union

from fastapi import FastAPI
from metamessage import mm

from mm_fastapi import MMRouter


# Models using @mm decorator
@mm(desc="Product model")
class Product:
    """Product model."""
    name: str = mm(desc="Product name")
    price: float = mm(desc="Price in USD")
    quantity: int = mm(desc="Stock quantity")
    description: Optional[str] = mm(desc="Product description", nullable=True)


@mm(desc="Product response")
class ProductResponse:
    """Product response with ID."""
    id: int = mm(desc="Product ID")
    name: str = mm(desc="Product name")
    price: float = mm(desc="Price in USD")
    quantity: int = mm(desc="Stock quantity")
    description: Optional[str] = mm(desc="Product description", nullable=True)


@mm(desc="Order model")
class Order:
    """Order model."""
    product_id: int = mm(desc="Product ID")
    quantity: int = mm(desc="Order quantity")
    customer_name: str = mm(desc="Customer name")
    customer_email: str = mm(desc="Customer email")


@mm(desc="Order response")
class OrderResponse:
    """Order response."""
    id: int = mm(desc="Order ID")
    product_id: int = mm(desc="Product ID")
    quantity: int = mm(desc="Order quantity")
    total: float = mm(desc="Total price")
    status: str = mm(desc="Order status")


@mm(desc="Generic API response")
class APIResponse:
    """Generic API response."""
    code: int = mm(desc="Response code")
    message: str = mm(desc="Response message")
    data: Optional[dict] = mm(desc="Response data", nullable=True)


@mm(desc="Error response")
class ErrorResponse:
    """Error response."""
    error: str = mm(desc="Error message")


# In-memory storage
products_db: dict[int, ProductResponse] = {}
orders_db: dict[int, OrderResponse] = {}
product_id_counter = 0
order_id_counter = 0


# Create app
app = FastAPI(
    title="E-Commerce API",
    description="Example e-commerce API with MetaMessage support",
    version="1.0.0",
)

# Create MMRouter with app auto-registration
router = MMRouter(app)


# Product endpoints
@router.post("/products")
async def create_product(req: Product) -> Union[APIResponse, ErrorResponse]:
    """Create a new product.

    Accepts MetaMessage binary format.
    Returns the created product with assigned ID.
    """
    global product_id_counter
    product_id_counter += 1

    response = ProductResponse(
        id=product_id_counter,
        name=req.name,
        price=req.price,
        quantity=req.quantity,
        description=req.description,
    )
    products_db[product_id_counter] = response

    return APIResponse(code=0, message="created", data=ProductResponse(
        id=product_id_counter,
        name=req.name,
        price=req.price,
        quantity=req.quantity,
        description=req.description,
    ))


@router.get("/products/{product_id}")
async def get_product(product_id: int) -> Union[ProductResponse, ErrorResponse]:
    """Get a product by ID.

    Response format determined by Accept header.
    """
    if product_id not in products_db:
        return ErrorResponse(error="Product not found")

    return products_db[product_id]


@router.get("/products")
async def list_products() -> List[ProductResponse]:
    """List all products."""
    return list(products_db.values())


@router.put("/products/{product_id}")
async def update_product(product_id: int, req: Product) -> Union[APIResponse, ErrorResponse]:
    """Update a product."""
    if product_id not in products_db:
        return ErrorResponse(error="Product not found")

    updated = ProductResponse(
        id=product_id,
        name=req.name,
        price=req.price,
        quantity=req.quantity,
        description=req.description,
    )
    products_db[product_id] = updated

    return APIResponse(code=0, message="updated", data=ProductResponse(
        id=product_id, name=req.name, price=req.price, quantity=req.quantity, description=req.description,
    ))


@router.delete("/products/{product_id}")
async def delete_product(product_id: int) -> Union[APIResponse, ErrorResponse]:
    """Delete a product."""
    if product_id not in products_db:
        return ErrorResponse(error="Product not found")

    del products_db[product_id]

    return APIResponse(code=0, message="deleted")


# Order endpoints
@router.post("/orders")
async def create_order(req: Order) -> Union[APIResponse, ErrorResponse]:
    """Create a new order."""
    global order_id_counter

    if req.product_id not in products_db:
        return ErrorResponse(error="Invalid product ID")

    product = products_db[req.product_id]

    if product.quantity < req.quantity:
        return ErrorResponse(error="Insufficient stock")

    order_id_counter += 1

    response = OrderResponse(
        id=order_id_counter,
        product_id=req.product_id,
        quantity=req.quantity,
        total=product.price * req.quantity,
        status="pending",
    )
    orders_db[order_id_counter] = response

    # Update stock
    product.quantity -= req.quantity

    return APIResponse(code=0, message="order created", data=OrderResponse(
        id=order_id_counter, product_id=req.product_id, quantity=req.quantity,
        total=product.price * req.quantity, status="pending",
    ))


@router.get("/orders/{order_id}")
async def get_order(order_id: int) -> Union[OrderResponse, ErrorResponse]:
    """Get an order by ID."""
    if order_id not in orders_db:
        return ErrorResponse(error="Order not found")

    return orders_db[order_id]


@router.get("/orders")
async def list_orders() -> List[OrderResponse]:
    """List all orders."""
    return list(orders_db.values())


# Echo endpoint to demonstrate format detection
@router.post("/echo")
async def echo_data(req: dict) -> dict:
    """Echo back the received data with format info.

    This endpoint demonstrates automatic body decoding.
    """
    return {
        "received_data": req,
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("E-Commerce API with MetaMessage Support")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  POST   /products      - Create product")
    print("  GET    /products      - List products")
    print("  GET    /products/{id} - Get product")
    print("  PUT    /products/{id} - Update product")
    print("  DELETE /products/{id} - Delete product")
    print("  POST   /orders        - Create order")
    print("  GET    /orders        - List orders")
    print("  GET    /orders/{id}   - Get order")
    print("  POST   /echo          - Echo with format info")
    print("\n" + "=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)