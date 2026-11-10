"""Cliente HTTP da API NASA FIRMS. Responsável apenas pela comunicação (sem parsing)."""

from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from firms_monitor.infrastructure.firms.queries import FirmsQuery

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/"


class FirmsApiError(RuntimeError):
    """Erro de comunicação ou resposta inválida da API FIRMS."""


class FirmsApiClient:
    def __init__(
        self,
        map_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        if not map_key:
            raise ValueError("FIRMS MAP_KEY não informada.")
        self._map_key = map_key
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout_seconds
        self._session = session or self._build_session(max_retries)

    @staticmethod
    def _build_session(max_retries: int) -> requests.Session:
        retry = Retry(
            total=max_retries,
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers.update({"User-Agent": "firms-monitor-rpa/1.0"})
        return session

    def fetch_csv(self, query: FirmsQuery) -> str:
        url = self._base_url + query.build_path(self._map_key)
        logger.debug("Consultando FIRMS: %s", url.replace(self._map_key, "***"))
        try:
            response = self._session.get(url, timeout=self._timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirmsApiError(f"Falha ao consultar a API FIRMS: {exc}".replace(self._map_key, "***")) from exc

        body = response.text.strip()
        # A FIRMS responde erros (ex.: "Invalid MAP_KEY.") com status 200 e texto puro.
        first_line = body.splitlines()[0] if body else ""
        if "latitude" not in first_line.lower():
            raise FirmsApiError(f"Resposta inesperada da API FIRMS: {body[:200]!r}")
        return body
