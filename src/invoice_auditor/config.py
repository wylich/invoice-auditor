from pathlib import Path
from typing import Tuple, Type

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class OpenAISettings(BaseModel):
    model: str = "openai:gpt-4o-mini"


class PathSettings(BaseModel):
    vat_lookup: Path = Path("data/lookup_dicts/vat_lookup.json")
    cvr_cache: Path = Path("src/invoice_auditor/storage/cvr_cache.json")


class CvrApiSettings(BaseModel):
    url: str = "https://cvrapi.dk/api"
    cache_days: int = 7


TOML_FILE = PROJECT_ROOT / "config.toml"


class Settings(BaseSettings):
    openai: OpenAISettings = OpenAISettings()
    paths: PathSettings = PathSettings()
    cvr_api: CvrApiSettings = CvrApiSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        **kwargs,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls, toml_file=TOML_FILE),)

    @property
    def vat_lookup_path(self) -> Path:
        return PROJECT_ROOT / self.paths.vat_lookup

    @property
    def cvr_cache_path(self) -> Path:
        return PROJECT_ROOT / self.paths.cvr_cache


settings = Settings()
