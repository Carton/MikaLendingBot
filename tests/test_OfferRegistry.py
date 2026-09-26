"""
Tests for the persistent offer registry (offer ownership tracking).
"""

import json

import pytest

from lendingbot.modules.OfferRegistry import (
    STATUS_OPEN,
    OfferRegistry,
    OfferRegistryError,
)


@pytest.fixture
def registry_path(tmp_path):
    return tmp_path / "offer_registry.json"


def make_registry(registry_path, account_key="abc123"):
    return OfferRegistry(registry_path, "Bitfinex", account_key)


def write_registry_file(registry_path, exchange="Bitfinex", account_key="abc123", orders=None):
    payload = {
        "version": 1,
        "exchange": exchange,
        "account_key": account_key,
        "orders": orders or {},
    }
    registry_path.write_text(json.dumps(payload), encoding="utf-8")


class TestLoadAndPersist:
    def test_missing_file_starts_empty(self, registry_path):
        registry = OfferRegistry.load(registry_path, "Bitfinex", "abc123")
        assert registry.order_count() == 0
        assert not registry.file_exists()

    def test_persist_and_reload_roundtrip(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 123, "20000", "0.0002", 30)
        registry.persist()

        loaded = OfferRegistry.load(registry_path, "Bitfinex", "abc123")
        assert loaded.order_count() == 1
        assert loaded.tracked_ids("USD") == {123}
        offer = loaded.get("USD", 123)
        assert offer is not None
        assert offer.status == STATUS_OPEN
        assert offer.original_amount == "20000"
        assert offer.remaining_amount == "20000"
        assert offer.rate == "0.0002"
        assert offer.duration_days == 30

    def test_persist_leaves_no_temp_file(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.persist()
        tmp = registry_path.with_name(registry_path.name + ".tmp")
        assert registry_path.exists()
        assert not tmp.exists()

    def test_persist_skips_unchanged(self, registry_path):
        registry = make_registry(registry_path)
        registry.persist(force=True)
        first_mtime = registry_path.stat().st_mtime_ns
        registry.persist()  # not dirty, no force -> no rewrite
        assert registry_path.stat().st_mtime_ns == first_mtime

    def test_account_key_is_stable_hash(self):
        assert OfferRegistry.account_key("key-one") == OfferRegistry.account_key("key-one")
        assert OfferRegistry.account_key("key-one") != OfferRegistry.account_key("key-two")
        assert OfferRegistry.account_key(None) == OfferRegistry.account_key("")
        assert len(OfferRegistry.account_key("key-one")) == 16


class TestLoadValidation:
    def test_corrupt_json_raises(self, registry_path):
        registry_path.write_text("{not json", encoding="utf-8")
        with pytest.raises(OfferRegistryError, match="cannot read"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_non_dict_payload_raises(self, registry_path):
        registry_path.write_text("[]", encoding="utf-8")
        with pytest.raises(OfferRegistryError, match="corrupt"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_unsupported_version_raises(self, registry_path):
        write_registry_file(registry_path)
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        data["version"] = 99
        registry_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(OfferRegistryError, match="unsupported version"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_exchange_mismatch_raises(self, registry_path):
        write_registry_file(registry_path, exchange="Poloniex")
        with pytest.raises(OfferRegistryError, match="belongs to exchange"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_account_mismatch_raises(self, registry_path):
        write_registry_file(registry_path, account_key="other")
        with pytest.raises(OfferRegistryError, match="different API account"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_invalid_entry_raises(self, registry_path):
        orders = {"USD:123": {"currency": "USD", "order_id": "123", "duration_days": "x"}}
        write_registry_file(registry_path, orders=orders)
        with pytest.raises(OfferRegistryError, match="corrupt"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")

    def test_entry_key_mismatch_raises(self, registry_path):
        orders = {
            "USD:123": {
                "currency": "USD",
                "order_id": "456",
                "original_amount": "1",
                "remaining_amount": "1",
                "rate": "0.0001",
                "duration_days": 2,
            }
        }
        write_registry_file(registry_path, orders=orders)
        with pytest.raises(OfferRegistryError, match="does not match"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")


class TestReconcile:
    def test_absent_order_is_removed(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.add("USD", 2, "20", "0.0001", 2)

        removed = registry.reconcile({"USD": [{"id": 2, "amount": "20"}]})

        assert removed == 1
        assert registry.tracked_ids("USD") == {2}

    def test_remaining_amount_updates_from_snapshot(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "100", "0.0001", 2)

        registry.reconcile({"USD": [{"id": 1, "amount": "62.5"}]})

        offer = registry.get("USD", 1)
        assert offer is not None
        assert offer.remaining_amount == "62.5"
        assert offer.original_amount == "100"

    def test_cancel_pending_still_open_reverts_to_open(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.mark_cancel_pending("USD", 1)

        registry.reconcile({"USD": [{"id": 1, "amount": "10"}]})

        offer = registry.get("USD", 1)
        assert offer is not None
        assert offer.status == STATUS_OPEN

    def test_cancel_pending_gone_is_removed(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.mark_cancel_pending("USD", 1)

        removed = registry.reconcile({"USD": []})

        assert removed == 1
        assert registry.get("USD", 1) is None

    def test_currency_without_offers_cleans_all(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.add("ETH", 7, "5", "0.0001", 2)

        removed = registry.reconcile({"ETH": [{"id": 7, "amount": "5"}]})

        assert removed == 1
        assert registry.tracked_ids("USD") == set()
        assert registry.tracked_ids("ETH") == {7}


class TestManagedFlag:
    def test_managed_flag_roundtrip(self, registry_path):
        registry = make_registry(registry_path)
        registry.add("USD", 1, "10", "0.0001", 2)
        registry.add("USD", 2, "20", "0.0002", 5, managed=False)
        registry.persist()

        loaded = OfferRegistry.load(registry_path, "Bitfinex", "abc123")
        assert loaded.tracked_ids("USD") == {1}
        assert loaded.preserved_ids("USD") == {2}
        preserved = loaded.get("USD", 2)
        assert preserved is not None
        assert preserved.managed is False

    def test_legacy_entry_without_managed_defaults_to_managed(self, registry_path):
        orders = {
            "USD:5": {
                "currency": "USD",
                "order_id": "5",
                "original_amount": "10",
                "remaining_amount": "10",
                "rate": "0.0001",
                "duration_days": 2,
            }
        }
        write_registry_file(registry_path, orders=orders)

        loaded = OfferRegistry.load(registry_path, "Bitfinex", "abc123")
        assert loaded.tracked_ids("USD") == {5}
        assert loaded.preserved_ids("USD") == set()

    def test_invalid_managed_flag_raises(self, registry_path):
        orders = {
            "USD:5": {
                "currency": "USD",
                "order_id": "5",
                "original_amount": "10",
                "remaining_amount": "10",
                "rate": "0.0001",
                "duration_days": 2,
                "managed": "maybe",
            }
        }
        write_registry_file(registry_path, orders=orders)
        with pytest.raises(OfferRegistryError, match="invalid managed flag"):
            OfferRegistry.load(registry_path, "Bitfinex", "abc123")
