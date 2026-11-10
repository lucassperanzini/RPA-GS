"""Leitura de contornos territoriais em GeoJSON (arquivo próprio ou embutido no pacote)."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from firms_monitor.domain.territory import Polygon, Territory

# Territórios embutidos no pacote: código -> arquivo em firms_monitor/data/
# BR: malha do IBGE (qualidade intermediária). Não inclui ilhas oceânicas (Fernando de Noronha,
# Trindade, Atol das Rocas), que de todo modo ficam fora do FIRMS_BBOX padrão.
BUILTIN_TERRITORIES = {
    "BR": "brasil.geojson",
}


class TerritoryLoadError(ValueError):
    pass


class GeoJsonTerritoryLoader:
    """Converte GeoJSON (Polygon, MultiPolygon, Feature ou FeatureCollection) em Territory."""

    def load(self, code_or_path: str) -> Territory:
        key = code_or_path.strip()
        if key.upper() in BUILTIN_TERRITORIES:
            return self._load_builtin(key.upper())
        path = Path(key)
        if not path.is_file():
            available = ", ".join(BUILTIN_TERRITORIES)
            raise TerritoryLoadError(
                f"Território '{key}' não encontrado. Use um código embutido ({available}) "
                "ou o caminho de um arquivo GeoJSON."
            )
        return self.from_geojson(path.stem, json.loads(path.read_text(encoding="utf-8")))

    def _load_builtin(self, code: str) -> Territory:
        resource = resources.files("firms_monitor.data").joinpath(BUILTIN_TERRITORIES[code])
        return self.from_geojson(code, json.loads(resource.read_text(encoding="utf-8")))

    def from_geojson(self, name: str, data: dict[str, Any]) -> Territory:
        polygons = [polygon for geometry in self._geometries(data) for polygon in self._polygons(geometry)]
        if not polygons:
            raise TerritoryLoadError(f"Nenhum polígono encontrado no GeoJSON '{name}'.")
        return Territory(name, polygons)

    def _geometries(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        kind = data.get("type")
        if kind == "FeatureCollection":
            return [f["geometry"] for f in data.get("features", []) if f.get("geometry")]
        if kind == "Feature":
            return [data["geometry"]] if data.get("geometry") else []
        return [data]

    @staticmethod
    def _polygons(geometry: dict[str, Any]) -> list[Polygon]:
        kind = geometry.get("type")
        if kind == "Polygon":
            coordinates = [geometry["coordinates"]]
        elif kind == "MultiPolygon":
            coordinates = geometry["coordinates"]
        else:
            raise TerritoryLoadError(f"Geometria '{kind}' não suportada (use Polygon ou MultiPolygon).")
        return [
            Polygon(
                exterior=tuple((float(x), float(y)) for x, y, *_ in rings[0]),
                holes=tuple(tuple((float(x), float(y)) for x, y, *_ in ring) for ring in rings[1:]),
            )
            for rings in coordinates
        ]
