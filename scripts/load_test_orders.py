#!/usr/bin/env python3
"""Submit fictional test orders through the backend API for local load testing."""

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


@dataclass
class SubmitResult:
    index: int
    ok: bool
    status: int | None
    order_id: str | None
    body: str
    error: str | None = None


def build_payload(index: int, mrn: str, provider_npi: str) -> dict[str, str]:
    """Build fictional, mock-safe intake data for one order."""
    return {
        "patient_name": f"Load Test Patient {index}",
        "mrn": mrn,
        "provider_name": "Dr. Load Test",
        "provider_npi": provider_npi,
        "diagnosis": "G70.00",
        "medication": "IVIG",
        "clinical_notes": (
            "Fictional local load-test note. No real patient, provider, or clinical data."
        ),
    }


def submit_order(base_url: str, index: int, mrn: str, provider_npi: str) -> SubmitResult:
    """Submit one order to POST /orders and return a structured result."""
    url = base_url.rstrip("/") + "/orders"
    data = json.dumps(build_payload(index, mrn, provider_npi)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            return SubmitResult(
                index=index,
                ok=200 <= response.status < 300,
                status=response.status,
                order_id=parsed.get("order_id"),
                body=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return SubmitResult(
            index=index,
            ok=False,
            status=exc.code,
            order_id=None,
            body=body,
            error=str(exc),
        )
    except Exception as exc:
        return SubmitResult(
            index=index,
            ok=False,
            status=None,
            order_id=None,
            body="",
            error=str(exc),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit fictional load-test orders through POST /orders.",
        epilog=(
            "Examples:\n"
            "  python scripts/load_test_orders.py --count 10 --concurrency 10\n"
            "  python scripts/load_test_orders.py --count 100 --concurrency 20\n"
            "  python scripts/load_test_orders.py --count 1000 --concurrency 50"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--start-mrn", type=int, default=900000)
    parser.add_argument("--provider-npi", default="1234567890")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be at least 1")

    started_at = time.perf_counter()
    results: list[SubmitResult] = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                submit_order,
                args.base_url,
                index,
                str(args.start_mrn + index),
                args.provider_npi,
            )
            for index in range(1, args.count + 1)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.perf_counter() - started_at
    succeeded = [result for result in results if result.ok]
    failed = [result for result in results if not result.ok]
    rate = args.count / elapsed if elapsed > 0 else 0

    print(f"Total requested: {args.count}")
    print(f"Total succeeded: {len(succeeded)}")
    print(f"Total failed: {len(failed)}")
    print(f"Elapsed seconds: {elapsed:.2f}")
    print(f"Approx requests/sec: {rate:.2f}")

    order_ids = [result.order_id for result in sorted(succeeded, key=lambda item: item.index)]
    print("First returned order_ids:")
    for order_id in order_ids[:10]:
        print(f"  {order_id}")

    if failed:
        print("Failed responses:")
        for result in sorted(failed, key=lambda item: item.index)[:20]:
            status = result.status if result.status is not None else "no-status"
            detail = result.body or result.error or "unknown error"
            print(f"  #{result.index} status={status} detail={detail}")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
