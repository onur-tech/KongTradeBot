"""Bright Data Web Unlocker Client für KongTradeBot + Aribas-Projekte."""
import os
import logging
from typing import Optional, Union

import requests

logger = logging.getLogger(__name__)


class BrightDataError(Exception):
    pass


class BrightDataClient:
    BASE_URL = "https://api.brightdata.com/request"

    def __init__(self, token: Optional[str] = None, zone: Optional[str] = None):
        self.token = token or os.getenv("BRIGHTDATA_API_TOKEN")
        self.zone = zone or os.getenv("BRIGHTDATA_WEB_UNLOCKER_ZONE", "mcp_unlocker")
        if not self.token:
            raise BrightDataError("BRIGHTDATA_API_TOKEN not set")

    def fetch(self, url: str, format: str = "raw", timeout: int = 60) -> Union[str, dict]:
        try:
            r = requests.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={"zone": self.zone, "url": url, "format": format},
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json() if format == "json" else r.text
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 401:
                raise BrightDataError("Auth failed — check token") from e
            if code == 422:
                raise BrightDataError(f"Zone '{self.zone}' invalid") from e
            raise BrightDataError(f"HTTP {code}") from e
        except requests.RequestException as e:
            raise BrightDataError(f"Request failed: {e}") from e
