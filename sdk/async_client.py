"""
Async MomoParse client backed by httpx.AsyncClient.
Drop-in for FastAPI, async Django, or any asyncio app.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from sdk.client import DEFAULT_BASE_URL, SANDBOX_KEY, _TIMEOUT, _raise_for
from sdk.models import BatchResult, ParseResult


class AsyncMomoParseClient:
    """
    Async client for the MomoParse API.

    Usage::

        from sdk import AsyncMomoParseClient

        async with AsyncMomoParseClient(api_key="sk-...") as client:
            result = await client.parse("Payment made for GHS 35.00 to ...")
            print(result.tx_type, result.amount)
    """

    def __init__(
        self,
        api_key: str = SANDBOX_KEY,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT,
        _transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers,
            timeout=timeout,
            transport=_transport,
        )

    async def parse(
        self,
        sms_text: str,
        *,
        sender_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ParseResult:
        """
        Parse a single MoMo SMS asynchronously.

        :param sms_text: Raw SMS text (required).
        :param sender_id: Sender ID from SMS metadata — improves telco detection.
        :param metadata: Arbitrary dict echoed back in the result.
        :returns: :class:`ParseResult`
        """
        payload: dict[str, Any] = {"sms_text": sms_text}
        if sender_id is not None:
            payload["sender_id"] = sender_id
        if metadata is not None:
            payload["metadata"] = metadata

        r = await self._http.post("/v1/parse", json=payload)
        _raise_for(r)
        return ParseResult._from_dict(r.json())

    async def parse_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> BatchResult:
        """
        Parse up to 100 MoMo SMS asynchronously.

        :param messages: List of dicts with keys ``sms_text`` (required),
                         ``sender_id`` (optional), ``metadata`` (optional).
        :returns: :class:`BatchResult`
        """
        r = await self._http.post("/v1/parse/batch", json={"messages": messages})
        _raise_for(r)
        return BatchResult._from_dict(r.json())

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncMomoParseClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
