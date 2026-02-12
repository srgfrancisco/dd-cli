"""Unified Datadog API client wrapper."""

import os
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api import (
    monitors_api,
    metrics_api,
    events_api,
    hosts_api,
    tags_api,
    service_checks_api,
)
from datadog_api_client.v2.api import logs_api, spans_api, service_definition_api
from ddogctl.config import DatadogConfig


class DatadogClient:
    """Unified Datadog API client."""

    def __init__(self, config: DatadogConfig):
        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = config.api_key
        configuration.api_key["appKeyAuth"] = config.app_key
        configuration.server_variables["site"] = config.site

        proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
        if proxy:
            configuration.proxy = proxy

        self.api_client = ApiClient(configuration)

        # V1 APIs
        self.monitors = monitors_api.MonitorsApi(self.api_client)
        self.metrics = metrics_api.MetricsApi(self.api_client)
        self.events = events_api.EventsApi(self.api_client)
        self.hosts = hosts_api.HostsApi(self.api_client)
        self.tags = tags_api.TagsApi(self.api_client)
        self.service_checks = service_checks_api.ServiceChecksApi(self.api_client)

        # V2 APIs
        self.logs = logs_api.LogsApi(self.api_client)
        self.spans = spans_api.SpansApi(self.api_client)
        self.service_definitions = service_definition_api.ServiceDefinitionApi(self.api_client)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.api_client.close()


def get_datadog_client() -> DatadogClient:
    """Get configured Datadog client."""
    from ddogctl.config import load_config

    config = load_config()
    return DatadogClient(config)
