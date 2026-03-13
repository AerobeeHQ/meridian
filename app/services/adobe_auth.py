"""
Adobe OAuth2 Authentication Service
Handles token acquisition and caching for Adobe Analytics API 2.0
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class OAuth2Auth:
    """OAuth2 Server-to-Server authentication for Adobe APIs"""

    TOKEN_ENDPOINT = "https://ims-na1.adobelogin.com/ims/token/v3"

    def __init__(self, client_id: str, client_secret: str, scopes: str | list[str] = None):
        """
        Initialize OAuth2 authentication

        Args:
            client_id: OAuth2 client ID from Adobe I/O Console
            client_secret: OAuth2 client secret
            scopes: Comma-separated string or list of OAuth2 scopes
        """
        self.client_id = client_id
        self.client_secret = client_secret

        # Handle scopes as string or list
        if isinstance(scopes, list):
            self.scopes = scopes
        elif isinstance(scopes, str):
            # Parse comma-separated string, strip whitespace
            self.scopes = [s.strip() for s in scopes.split(',')]
        else:
            # Default scopes for Adobe Analytics
            self.scopes = ["openid", "AdobeID", "additional_info.projectedProductContext"]

        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary

        Returns:
            Valid access token string

        Raises:
            requests.HTTPError: If token acquisition fails
        """
        # Return cached token if still valid (with 5 min buffer)
        if self._access_token and self._token_expires_at:
            buffer_time = datetime.now() + timedelta(minutes=5)
            if buffer_time < self._token_expires_at:
                logger.debug("Using cached access token (expires %s)", self._token_expires_at)
                return self._access_token

        # Fetch new token
        logger.info("Fetching new OAuth2 access token")
        self._access_token, self._token_expires_at = self._fetch_token()
        return self._access_token

    def _fetch_token(self) -> Tuple[str, datetime]:
        """
        Fetch a new access token from Adobe IMS

        Returns:
            Tuple of (access_token, expiration_datetime)

        Raises:
            requests.HTTPError: If token request fails
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": ",".join(self.scopes)
        }

        logger.debug("Requesting token with scopes: %s", self.scopes)

        response = requests.post(
            self.TOKEN_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if not response.ok:
            logger.error(
                "Token acquisition failed: %s %s - %s",
                response.status_code,
                response.reason,
                response.text
            )
            response.raise_for_status()

        data = response.json()
        access_token = data["access_token"]
        expires_in = data.get("expires_in", 86399)  # Default ~24 hours
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        logger.info("Access token acquired, expires at %s", expires_at.isoformat())
        return access_token, expires_at

    def clear_token(self):
        """Clear the cached token (useful for forcing re-authentication)"""
        self._access_token = None
        self._token_expires_at = None
        logger.debug("Token cache cleared")

    @property
    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        if not self._access_token or not self._token_expires_at:
            return False
        return datetime.now() < self._token_expires_at

