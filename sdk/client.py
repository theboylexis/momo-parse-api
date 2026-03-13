"""
Synchronous MomoParse client backed by httpx.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from sdk.exceptions import AuthError, MomoParseError, RateLimitError, ServerError, ValidationError
from sdk.models import BatchResult, ParseResult

DEFAULT_BASE_URL = "https://api.momoparse.com"
SANDBOX_KEY = "sk-sandbox-momoparse"
_TIMEOUT = 30.0


def _raise_for(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        body = response.json()
        detail = body.get("detail") or body
        if isinstance(detail, dict):
            msg = detail.get("message", response.text)
            code = detail.get("error_code")
        else:
            msg = str(detail)
            code = None
    except Exception:
        msg = response.text
        code = None

    status = response.status_code
    if status == 401:
        raise AuthError(msg, status_code=status, error_code=code)
    if status == 422:
        raise ValidationError(msg, status_code=status, error_code=code)
    if status == 429:
        raise RateLimitError(msg, status_code=status, error_code=code)
    if status >= 500:
        raise ServerError(msg, status_code=status, error_code=code)
    raise MomoParseError(msg, status_code=status, error_code=code)


class MomoParseClient:
    """
    Synchronous client for the MomoParse API.

    Usage::

        from sdk import MomoParseClient

        client = MomoParseClient(api_key="sk-...")
        result = client.parse("Payment made for GHS 35.00 to ...", sender_id="MobileMoney")
        print(result.tx_type, result.amount)
    """

    def __init__(
        self,
        api_key: str = SANDBOX_KEY,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT,
        _transport: Optional[httpx.BaseTransport] = None,
    ):
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self._http = httpx.Client(
            base_url=base_url,
            headers=self._headers,
            timeout=timeout,
            transport=_transport,
        )

    def parse(
        self,
        sms_text: str,
        *,
        sender_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ParseResult:
        """
        Parse a single MoMo SMS.

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

        r = self._http.post("/v1/parse", json=payload)
        _raise_for(r)
        return ParseResult._from_dict(r.json())

    def parse_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> BatchResult:
        """
        Parse up to 100 MoMo SMS in one request.

        :param messages: List of dicts with keys ``sms_text`` (required),
                         ``sender_id`` (optional), ``metadata`` (optional).
        :returns: :class:`BatchResult`
        """
        r = self._http.post("/v1/parse/batch", json={"messages": messages})
        _raise_for(r)
        return BatchResult._from_dict(r.json())

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "MomoParseClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
