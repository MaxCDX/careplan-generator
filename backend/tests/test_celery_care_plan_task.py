import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def make_order(status="queued"):
    patient = SimpleNamespace(id="patient-1", name="Test Patient", mrn="123456", dob=None)
    provider = SimpleNamespace(id="provider-1", name="Dr. Test", npi="1234567890")
    return SimpleNamespace(
        id="order-1",
        patient=patient,
        provider=provider,
        medication="IVIG",
        diagnosis="G70.00",
        clinical_notes="Fictional clinical note.",
        status=status,
        error_message="previous error",
        care_plan=None,
    )


class FakeQuery:
    def __init__(self, order):
        self.order = order

    def filter(self, *args, **kwargs):
        return self

    def one_or_none(self):
        return self.order


class FakeDb:
    def __init__(self, order):
        self.order = order
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.added = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, item):
        pass

    def query(self, model):
        return FakeQuery(self.order)

    def close(self):
        self.closed = True


class FakeTaskSelf:
    def __init__(self, retries=0, retry_exc=None):
        self.request = SimpleNamespace(retries=retries)
        self.retry_calls = []
        self.retry_exc = retry_exc or RuntimeError("celery retry requested")

    def retry(self, exc, countdown):
        self.retry_calls.append((exc, countdown))
        raise self.retry_exc


def test_generate_care_plan_task_marks_order_completed_and_creates_care_plan(monkeypatch):
    from app.tasks import care_plan_tasks

    order = make_order()
    db = FakeDb(order)
    created = []

    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        care_plan_tasks,
        "generate_care_plan_content",
        lambda order, model: "generated care plan",
    )
    monkeypatch.setattr(care_plan_tasks, "get_openai_model", lambda: "test-model")
    monkeypatch.setattr(
        care_plan_tasks.care_plan_repository,
        "create_care_plan",
        lambda db, order, care_plan_content, model: created.append(
            (order.id, care_plan_content, model)
        ),
    )

    result = care_plan_tasks.process_order_for_celery(FakeTaskSelf(), "order-1")

    assert result == {"status": "completed", "order_id": "order-1"}
    assert order.status == "completed"
    assert order.error_message is None
    assert created == [("order-1", "generated care plan", "test-model")]
    assert db.closed is True


def test_generate_care_plan_task_skips_missing_order(monkeypatch):
    from app.tasks import care_plan_tasks

    db = FakeDb(order=None)
    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)

    result = care_plan_tasks.process_order_for_celery(FakeTaskSelf(), "missing-order")

    assert result == {"status": "order_not_found", "order_id": "missing-order"}
    assert db.commits == 0
    assert db.closed is True


def test_generate_care_plan_task_skips_non_queued_order(monkeypatch):
    from app.tasks import care_plan_tasks

    order = make_order(status="completed")
    db = FakeDb(order)
    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)

    result = care_plan_tasks.process_order_for_celery(FakeTaskSelf(), "order-1")

    assert result == {"status": "skipped", "order_id": "order-1"}
    assert order.status == "completed"
    assert db.commits == 0
    assert db.closed is True


def test_generate_care_plan_task_allows_processing_order_on_retry(monkeypatch):
    from app.tasks import care_plan_tasks

    order = make_order(status="processing")
    db = FakeDb(order)
    created = []

    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        care_plan_tasks,
        "generate_care_plan_content",
        lambda order, model: "generated care plan",
    )
    monkeypatch.setattr(care_plan_tasks, "get_openai_model", lambda: "test-model")
    monkeypatch.setattr(
        care_plan_tasks.care_plan_repository,
        "create_care_plan",
        lambda db, order, care_plan_content, model: created.append(
            (order.id, care_plan_content, model)
        ),
    )

    result = care_plan_tasks.process_order_for_celery(FakeTaskSelf(retries=1), "order-1")

    assert result == {"status": "completed", "order_id": "order-1"}
    assert order.status == "completed"
    assert created == [("order-1", "generated care plan", "test-model")]


def test_generate_care_plan_task_uses_celery_retry_before_final_failure(monkeypatch):
    from app.tasks import care_plan_tasks

    order = make_order()
    db = FakeDb(order)

    def fail_generation(order, model):
        raise RuntimeError("temporary outage with possible sensitive context")

    task_self = FakeTaskSelf(retries=0)
    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(care_plan_tasks, "generate_care_plan_content", fail_generation)
    monkeypatch.setattr(care_plan_tasks, "get_openai_model", lambda: "test-model")

    try:
        care_plan_tasks.process_order_for_celery(task_self, "order-1")
    except RuntimeError as exc:
        assert str(exc) == "celery retry requested"

    assert len(task_self.retry_calls) == 1
    assert task_self.retry_calls[0][1] == care_plan_tasks.get_retry_countdown(0)
    assert order.status == "processing"
    assert order.error_message is None
    assert db.rollbacks == 1


def test_generate_care_plan_task_marks_failed_with_safe_message_after_final_retry(monkeypatch):
    from app.tasks import care_plan_tasks

    order = make_order()
    db = FakeDb(order)
    created = []

    def fail_generation(order, model):
        raise RuntimeError("raw stack details with possible sensitive context")

    task_self = FakeTaskSelf(retries=care_plan_tasks.MAX_RETRIES)
    monkeypatch.setattr(care_plan_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(care_plan_tasks, "generate_care_plan_content", fail_generation)
    monkeypatch.setattr(care_plan_tasks, "get_openai_model", lambda: "test-model")
    monkeypatch.setattr(care_plan_tasks.care_plan_repository, "create_care_plan", lambda *args, **kwargs: created.append(args))

    result = care_plan_tasks.process_order_for_celery(task_self, "order-1")

    assert result == {"status": "failed", "order_id": "order-1"}
    assert order.status == "failed"
    assert order.error_message == care_plan_tasks.WORKER_FAILURE_MESSAGE
    assert created == []
    assert db.rollbacks == 1
    assert db.closed is True
