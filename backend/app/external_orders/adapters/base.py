from app.orders.schemas import OrderCreate


class BaseIntakeAdapter:
    """Template Method base for source-specific order intake normalization."""

    def normalize(self, payload: dict) -> OrderCreate:
        parsed = self.parse(payload)
        return self.transform(parsed)

    def parse(self, payload: dict):
        raise NotImplementedError

    def transform(self, parsed) -> OrderCreate:
        raise NotImplementedError
