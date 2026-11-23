"""Route adapters: one per kind of authoritative run record."""

from .base import Adapter
from .cli_sessions import CliSessionsAdapter
from .fire_ledger import FireLedgerAdapter
from .gateway_api import GatewayStatusAdapter
from .webhook_log import WebhookLogAdapter

ADAPTER_TYPES = {
    "gateway": GatewayStatusAdapter,
    "cli-sessions": CliSessionsAdapter,
    "fire-ledger": FireLedgerAdapter,
    "webhook": WebhookLogAdapter,
}

__all__ = [
    "Adapter",
    "ADAPTER_TYPES",
    "CliSessionsAdapter",
    "FireLedgerAdapter",
    "GatewayStatusAdapter",
    "WebhookLogAdapter",
]
