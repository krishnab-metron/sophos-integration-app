"""Sophos Central API client.

This module provides a :class:`SophosAPIClient` class that encapsulates
authentication, tenant discovery and endpoint retrieval for Sophos Central.

"""

from __future__ import annotations

import time
import logging
from typing import Dict, Iterable, Optional, Iterator, List

import requests


LOGGER = logging.getLogger(__name__)


class SophosAPIError(Exception):
    """Raised when an error occurs while interacting with Sophos APIs."""
    pass


class SophosAPIClient:
    """Client to interact with Sophos Central APIs."""

    ID_TOKEN_URL: str = "https://id.sophos.com/api/v2/oauth2/token"
    WHOAMI_URL: str = "https://api.central.sophos.com/whoami/v1"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._tenant_id: Optional[str] = None
        self._data_region: Optional[str] = None

    # Authentication
    def _authenticate(self) -> None:
        """Obtain a bearer token using the client credentials flow.

        Caches the token until 60 seconds before expiry.
        """
        if self._token and time.time() < self._token_expiry - 60:
            return

        LOGGER.debug("Fetching new Sophos OAuth token")
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "token",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(self.ID_TOKEN_URL, data=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise SophosAPIError(
                f"Token request failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        self._token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))
        self._token_expiry = time.time() + expires_in
        LOGGER.info("Obtained token valid for %s seconds", expires_in)

    # Tenant discovery
    def _discover_tenant(self) -> None:
        if self._tenant_id and self._data_region:
            return
        self._authenticate()
        resp = requests.get(
            self.WHOAMI_URL,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise SophosAPIError(
                f"Failed to call whoami API: {resp.status_code} {resp.text}"
            )
        info = resp.json()
        tenant_id = info.get("id")
        data_region = info.get("apiHosts", {}).get("dataRegion")
        if not tenant_id or not data_region:
            raise SophosAPIError(
                f"whoami response missing id or dataRegion: {info}"
            )
        self._tenant_id = tenant_id
        self._data_region = data_region.rstrip("/")
        LOGGER.info("Discovered tenant %s using data region %s", tenant_id, data_region)

    def _headers(self) -> Dict[str, str]:
        self._authenticate()
        self._discover_tenant()
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Tenant-ID": self._tenant_id,
        }

    # Endpoint retrieval
    def list_endpoints(
        self,
        fields: Optional[Iterable[str]] = None,
        view: Optional[str] = None,
        page_size: int = 100,
    ) -> Iterator[Dict[str, object]]:
        """Yield endpoint dictionaries for the entire tenant."""
        
        headers = self._headers()
        params: Dict[str, object] = {"pageSize": page_size}
        if fields:
            params["fields"] = ",".join(fields)
        if view:
            params["view"] = view
        next_key: Optional[str] = None
        while True:
            if next_key:
                params["pageFromKey"] = next_key
            url = f"{self._data_region}/endpoint/v1/endpoints"
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            if resp.status_code != 200:
                raise SophosAPIError(
                    f"Endpoint list request failed: {resp.status_code} {resp.text}"
                )
            body = resp.json()
            items: List[Dict[str, object]] = body.get("items", [])
            for item in items:
                yield item
            next_key = body.get("pages", {}).get("nextKey") if body.get("pages") else None
            if not next_key:
                break