"""Configuration management for Datadog CLI."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import sys
from rich.console import Console

console = Console()


class DatadogConfig(BaseSettings):
    """Datadog configuration from environment variables."""

    api_key: str = Field(..., alias="DD_API_KEY")
    app_key: str = Field(..., alias="DD_APP_KEY")
    site: str = Field(default="datadoghq.com", alias="DD_SITE")

    # Client settings
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0

    # Display options
    default_format: str = "table"
    color_output: bool = True

    # Investigation presets
    default_time_range: str = "1h"

    model_config = SettingsConfigDict(
        env_file=".envrc",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("site")
    @classmethod
    def expand_region_shortcut(cls, v: str) -> str:
        """Support dogshell-style region shortcuts."""
        regions = {
            "us": "datadoghq.com",
            "eu": "datadoghq.eu",
            "us3": "us3.datadoghq.com",
            "us5": "us5.datadoghq.com",
            "ap1": "ap1.datadoghq.com",
            "gov": "ddog-gov.com",
        }
        return regions.get(v.lower(), v)


def load_config() -> DatadogConfig:
    """Load and validate configuration."""
    try:
        return DatadogConfig()
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\n[yellow]Required environment variables:[/yellow]")
        console.print("  - DD_API_KEY")
        console.print("  - DD_APP_KEY")
        console.print("  - DD_SITE (optional, defaults to datadoghq.com)")
        console.print("\n[yellow]Supported regions:[/yellow] us, eu, us3, us5, ap1, gov")
        console.print("\n[dim]Make sure to source .envrc: direnv allow[/dim]")
        sys.exit(1)
