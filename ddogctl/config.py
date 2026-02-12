"""Configuration management for Datadog CLI."""

import json
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import sys
from rich.console import Console

console = Console()


def get_config_path() -> str:
    """Return the path to the config file (~/.ddogctl/config.json)."""
    return os.path.join(os.path.expanduser("~"), ".ddogctl", "config.json")


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


def _load_profile_data(profile: str | None = None) -> dict | None:
    """Load profile data from config file.

    Args:
        profile: Profile name to load. If None, uses DDOGCTL_PROFILE env var
                 or active_profile from config file.

    Returns:
        Dict with api_key, app_key, site from the profile, or None if not found.
    """
    config_path = get_config_path()

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    profiles = data.get("profiles", {})
    if not profiles:
        return None

    # Determine which profile to use
    if profile is None:
        profile = os.environ.get("DDOGCTL_PROFILE", data.get("active_profile", ""))

    if not profile or profile not in profiles:
        if profile:
            # Explicitly requested profile that doesn't exist
            return {"_error": f"Profile '{profile}' not found"}
        return None

    return profiles[profile]


def load_config(profile: str | None = None) -> DatadogConfig:
    """Load and validate configuration.

    Priority: CLI flag > env var > active profile > defaults

    Args:
        profile: Optional profile name to use. If specified, loads from
                 the named profile in ~/.ddogctl/config.json.
    """
    # Check if env vars are set
    has_env_api_key = "DD_API_KEY" in os.environ
    has_env_app_key = "DD_APP_KEY" in os.environ

    # If both env vars are set and no explicit profile requested, use env vars directly
    if has_env_api_key and has_env_app_key and profile is None:
        # No explicit profile, and env vars exist -- still check DDOGCTL_PROFILE
        ddogctl_profile = os.environ.get("DDOGCTL_PROFILE")
        if not ddogctl_profile:
            try:
                return DatadogConfig()
            except Exception as e:
                console.print(f"[red]Configuration error: {e}[/red]")
                _print_config_help()
                sys.exit(1)

    # Try loading from profile
    profile_data = _load_profile_data(profile)

    if profile_data and "_error" in profile_data:
        console.print(f"[red]{profile_data['_error']}[/red]")
        sys.exit(1)

    if profile_data:
        # Use profile data as base, let env vars override
        kwargs = {}
        kwargs["DD_API_KEY"] = os.environ.get("DD_API_KEY", profile_data.get("api_key", ""))
        kwargs["DD_APP_KEY"] = os.environ.get("DD_APP_KEY", profile_data.get("app_key", ""))
        kwargs["DD_SITE"] = os.environ.get("DD_SITE", profile_data.get("site", "datadoghq.com"))

        try:
            return DatadogConfig(**kwargs)
        except Exception as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            _print_config_help()
            sys.exit(1)

    # No profile data available, fall back to env vars
    try:
        return DatadogConfig()
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        _print_config_help()
        sys.exit(1)


def _print_config_help() -> None:
    """Print configuration help text."""
    console.print("\n[yellow]Required environment variables:[/yellow]")
    console.print("  - DD_API_KEY")
    console.print("  - DD_APP_KEY")
    console.print("  - DD_SITE (optional, defaults to datadoghq.com)")
    console.print("\n[yellow]Supported regions:[/yellow] us, eu, us3, us5, ap1, gov")
    console.print("\n[dim]Or configure a profile: ddogctl config init[/dim]")
