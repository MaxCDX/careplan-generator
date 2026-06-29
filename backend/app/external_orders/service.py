from app.external_orders.factory import get_external_order_adapter
from app.orders.schemas import OrderCreate


def normalize_external_order(source: str, payload: dict) -> OrderCreate:
    """Normalize one external source payload into the existing OrderCreate schema."""
    adapter = get_external_order_adapter(source)
    return adapter.normalize(payload)
