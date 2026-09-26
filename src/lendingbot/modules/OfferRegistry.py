"""Persistent registry of loan offers created by this bot.

The registry is the authority for offer ownership: with
``cancel_policy = "own"`` the bot only cancels offers whose ids appear here.
Offers that are open on the exchange but missing from the registry (manual
placements, offers created by other tools, or offers created in the crash
window between a successful create and the registry write) are never touched.

The file is written atomically (temp file + replace) and validated strictly on
load: a corrupt file, an unsupported version, or a file belonging to a
different exchange/account is an error, never silently treated as an empty
registry. Callers must pause canceling and placing offers in that case.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import threading
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


REGISTRY_VERSION = 1

STATUS_OPEN = "open"
STATUS_CANCEL_PENDING = "cancel_pending"
_VALID_STATUSES = {STATUS_OPEN, STATUS_CANCEL_PENDING}


class OfferRegistryError(Exception):
    """Raised when the registry file cannot be trusted."""


@dataclass
class TrackedOffer:
    currency: str
    order_id: int
    original_amount: str
    remaining_amount: str
    rate: str
    duration_days: int
    status: str = STATUS_OPEN
    # managed offers are refreshed (canceled and re-placed) by the bot each
    # cycle; preserved offers (carved remainders re-placed at their original
    # rate and duration) are never refreshed, only identifiable for
    # observability and future absorption.
    managed: bool = True
    created_at: str = ""
    last_seen_at: str = ""

    def key(self) -> str:
        return f"{self.currency}:{self.order_id}"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _parse_decimal(value: object, context: str) -> str:
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, TypeError, ValueError) as ex:
        raise OfferRegistryError(f"{context}: not a valid decimal: {value!r}") from ex


class OfferRegistry:
    """Tracks which open loan offers this bot created."""

    def __init__(self, path: str | Path, exchange: str, account_key: str) -> None:
        self._path = Path(path)
        self._exchange = exchange
        self._account_key = account_key
        self._orders: dict[str, TrackedOffer] = {}
        self._lock = threading.RLock()
        self._dirty = False

    # --- Construction ---

    @staticmethod
    def account_key(apikey: str | None) -> str:
        """Stable, non-secret identifier for the API account."""
        if not apikey:
            return "no-apikey"
        return hashlib.sha256(apikey.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def load(cls, path: str | Path, exchange: str, account_key: str) -> OfferRegistry:
        """Loads and validates the registry; missing file starts empty."""
        registry = cls(path, exchange, account_key)
        registry_path = Path(path)
        if not registry_path.exists():
            return registry

        try:
            raw = registry_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as ex:
            raise OfferRegistryError(
                f"cannot read offer registry '{registry_path}' ({ex}); "
                "fix or remove the file, or set bot.offer_registry_file"
            ) from ex

        if not isinstance(data, dict):
            raise OfferRegistryError(f"offer registry '{registry_path}' is corrupt")

        version = data.get("version")
        if version != REGISTRY_VERSION:
            raise OfferRegistryError(
                f"offer registry '{registry_path}' has unsupported version {version!r} "
                f"(expected {REGISTRY_VERSION})"
            )

        file_exchange = data.get("exchange")
        if file_exchange != exchange:
            raise OfferRegistryError(
                f"offer registry '{registry_path}' belongs to exchange {file_exchange!r}, "
                f"but this bot runs on {exchange!r}; remove the file or point "
                "bot.offer_registry_file elsewhere"
            )

        file_account = data.get("account_key")
        if file_account != account_key:
            raise OfferRegistryError(
                f"offer registry '{registry_path}' belongs to a different API account; "
                "remove the file or point bot.offer_registry_file elsewhere"
            )

        orders = data.get("orders", {})
        if not isinstance(orders, dict):
            raise OfferRegistryError(f"offer registry '{registry_path}' is corrupt")

        for key, entry in orders.items():
            tracked = cls._parse_entry(key, entry, registry_path)
            if tracked.key() != key:
                raise OfferRegistryError(
                    f"offer registry '{registry_path}': entry key {key!r} does not match "
                    f"its contents ({tracked.key()!r})"
                )
            registry._orders[key] = tracked

        return registry

    @classmethod
    def _parse_entry(cls, key: str, entry: object, registry_path: Path) -> TrackedOffer:
        if not isinstance(entry, dict):
            raise OfferRegistryError(f"offer registry '{registry_path}': entry {key!r} is corrupt")
        try:
            currency = str(entry["currency"])
            order_id = int(str(entry["order_id"]))
            status = str(entry.get("status", STATUS_OPEN))
            duration_days = int(entry["duration_days"])
        except (KeyError, TypeError, ValueError) as ex:
            raise OfferRegistryError(
                f"offer registry '{registry_path}': entry {key!r} is corrupt ({ex})"
            ) from ex

        if not currency or order_id <= 0:
            raise OfferRegistryError(
                f"offer registry '{registry_path}': entry {key!r} has invalid identity"
            )
        if status not in _VALID_STATUSES:
            raise OfferRegistryError(
                f"offer registry '{registry_path}': entry {key!r} has invalid status {status!r}"
            )

        return TrackedOffer(
            currency=currency,
            order_id=order_id,
            original_amount=_parse_decimal(entry.get("original_amount", ""), f"entry {key!r}"),
            remaining_amount=_parse_decimal(entry.get("remaining_amount", ""), f"entry {key!r}"),
            rate=_parse_decimal(entry.get("rate", ""), f"entry {key!r}"),
            duration_days=duration_days,
            status=status,
            managed=cls._parse_managed(entry.get("managed", True), key),
            created_at=str(entry.get("created_at", "")),
            last_seen_at=str(entry.get("last_seen_at", "")),
        )

    @staticmethod
    def _parse_managed(value: object, key: str) -> bool:
        # Older files have no "managed" field; they only held managed offers.
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise OfferRegistryError(f"offer registry entry {key!r}: invalid managed flag {value!r}")

    # --- Queries ---

    def file_exists(self) -> bool:
        return self._path.exists()

    def tracked_ids(self, currency: str) -> set[int]:
        """Ids of managed offers (refresh candidates) for a currency."""
        with self._lock:
            return {
                offer.order_id
                for offer in self._orders.values()
                if offer.currency == currency and offer.managed
            }

    def preserved_ids(self, currency: str) -> set[int]:
        """Ids of preserved offers (carved remainders) for a currency."""
        with self._lock:
            return {
                offer.order_id
                for offer in self._orders.values()
                if offer.currency == currency and not offer.managed
            }

    def order_count(self) -> int:
        with self._lock:
            return len(self._orders)

    def get(self, currency: str, order_id: int) -> TrackedOffer | None:
        with self._lock:
            return self._orders.get(f"{currency}:{order_id}")

    # --- Mutations ---

    def add(
        self,
        currency: str,
        order_id: int,
        amount: str,
        rate: str,
        duration_days: int,
        managed: bool = True,
    ) -> None:
        """Records a newly created offer; caller is responsible for persist()."""
        if order_id <= 0:
            return
        now = _utc_now_iso()
        amount_s = _parse_decimal(amount, "registry add")
        rate_s = _parse_decimal(rate, "registry add")
        with self._lock:
            self._orders[f"{currency}:{order_id}"] = TrackedOffer(
                currency=currency,
                order_id=order_id,
                original_amount=amount_s,
                remaining_amount=amount_s,
                rate=rate_s,
                duration_days=duration_days,
                status=STATUS_OPEN,
                managed=managed,
                created_at=now,
                last_seen_at=now,
            )
            self._dirty = True

    def mark_cancel_pending(self, currency: str, order_id: int) -> None:
        """Flags that a cancel was requested; reconcile() resolves the outcome."""
        with self._lock:
            offer = self._orders.get(f"{currency}:{order_id}")
            if offer is not None and offer.status != STATUS_CANCEL_PENDING:
                offer.status = STATUS_CANCEL_PENDING
                self._dirty = True

    def reconcile(self, open_offers: dict[str, list[dict[str, object]]]) -> int:
        """Aligns the registry with a fresh, complete snapshot of open offers.

        Orders absent from the snapshot are removed (canceled or fully filled).
        A cancel-pending order that is still open reverts to open so the cancel
        is retried next cycle. Returns the number of removed orders.
        """
        removed = 0
        now = _utc_now_iso()
        with self._lock:
            for key, offer in list(self._orders.items()):
                snapshot_offer = self._find(open_offers, offer.currency, offer.order_id)
                if snapshot_offer is None:
                    del self._orders[key]
                    removed += 1
                    self._dirty = True
                    continue
                amount = _parse_decimal(
                    snapshot_offer.get("amount", offer.remaining_amount), f"reconcile {key}"
                )
                if offer.remaining_amount != amount:
                    offer.remaining_amount = amount
                    self._dirty = True
                if offer.status == STATUS_CANCEL_PENDING:
                    offer.status = STATUS_OPEN
                    self._dirty = True
                offer.last_seen_at = now
            if removed:
                self._dirty = True
        return removed

    @staticmethod
    def _find(
        open_offers: dict[str, list[dict[str, object]]], currency: str, order_id: int
    ) -> dict[str, object] | None:
        for offer in open_offers.get(currency, []):
            raw_id = offer.get("id")
            if raw_id is None:
                continue
            try:
                if int(str(raw_id)) == order_id:
                    return offer
            except (TypeError, ValueError):
                continue
        return None

    # --- Persistence ---

    def is_dirty(self) -> bool:
        with self._lock:
            return self._dirty

    def persist(self, force: bool = False) -> None:
        """Atomically writes the registry unless unchanged (or force=True)."""
        with self._lock:
            if not self._dirty and not force and self._path.exists():
                return
            payload = {
                "version": REGISTRY_VERSION,
                "exchange": self._exchange,
                "account_key": self._account_key,
                "orders": {key: offer.__dict__ for key, offer in sorted(self._orders.items())},
            }
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_name(self._path.name + ".tmp")
            tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            tmp_path.replace(self._path)
            self._dirty = False
