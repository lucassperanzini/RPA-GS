"""Configuração centralizada, lida de variáveis de ambiente (ou arquivo .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from firms_monitor.domain.models import RiskLevel


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Settings:
    map_key: str
    source: str = "VIIRS_NOAA20_NRT"
    query_mode: str = "country"  # "country" ou "area"
    country_code: str = "BRA"
    bbox: tuple[float, float, float, float] | None = None  # west, south, east, north
    day_range: int = 1
    base_url: str = "https://firms.modaps.eosdis.nasa.gov/"
    timeout_seconds: float = 60.0
    max_retries: int = 3

    risk_medio_frp: float = 10.0
    risk_alto_frp: float = 50.0
    risk_critico_frp: float = 100.0
    alert_min_level: RiskLevel = RiskLevel.CRITICO
    min_numeric_confidence: int = 30
    min_frp: float = 0.0

    output_csv: Path = Path("data/ocorrencias.csv")
    csv_delimiter: str = ","
    log_file: Path | None = Path("logs/firms_monitor.log")
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, dotenv_path: str | Path | None = ".env") -> "Settings":
        if env is None:
            _load_dotenv(dotenv_path)
            env = os.environ

        def get(name: str, default: str) -> str:
            return env.get(name, default).strip()

        try:
            log_file = get("LOG_FILE", "logs/firms_monitor.log")
            bbox_raw = get("FIRMS_BBOX", "")
            return cls(
                map_key=_required(env, "FIRMS_MAP_KEY"),
                source=get("FIRMS_SOURCE", "VIIRS_NOAA20_NRT"),
                query_mode=get("FIRMS_QUERY_MODE", "country").lower(),
                country_code=get("FIRMS_COUNTRY", "BRA").upper(),
                bbox=_parse_bbox(bbox_raw) if bbox_raw else None,
                day_range=int(get("FIRMS_DAY_RANGE", "1")),
                base_url=get("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/"),
                timeout_seconds=float(get("FIRMS_TIMEOUT_SECONDS", "60")),
                max_retries=int(get("FIRMS_MAX_RETRIES", "3")),
                risk_medio_frp=float(get("RISK_MEDIO_FRP", "10")),
                risk_alto_frp=float(get("RISK_ALTO_FRP", "50")),
                risk_critico_frp=float(get("RISK_CRITICO_FRP", "100")),
                alert_min_level=RiskLevel.from_name(get("ALERT_MIN_LEVEL", "CRITICO")),
                min_numeric_confidence=int(get("MIN_NUMERIC_CONFIDENCE", "30")),
                min_frp=float(get("MIN_FRP", "0")),
                output_csv=Path(get("OUTPUT_CSV", "data/ocorrencias.csv")),
                csv_delimiter=get("CSV_DELIMITER", ",") or ",",
                log_file=Path(log_file) if log_file else None,
                log_level=get("LOG_LEVEL", "INFO").upper(),
            )
        except ConfigurationError:
            raise
        except ValueError as exc:
            raise ConfigurationError(f"Configuração inválida: {exc}") from exc


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Variável obrigatória '{name}' não definida. "
            "Obtenha uma MAP_KEY gratuita em https://firms.modaps.eosdis.nasa.gov/api/map_key/"
        )
    return value


def _parse_bbox(raw: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in raw.split(",")]
    if len(parts) != 4:
        raise ValueError("FIRMS_BBOX deve ter o formato west,south,east,north")
    return parts[0], parts[1], parts[2], parts[3]


def _load_dotenv(path: str | Path | None) -> None:
    """Carrega o .env se python-dotenv estiver instalado (dependência opcional)."""
    if path is None:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(path)
