"""Spans API helper for aggregate_spans wrapper."""


def aggregate_spans(client, filter_dict, compute_list, group_by_list=None):
    """Call aggregate_spans with proper data envelope and normalize response.

    The Datadog SDK v2 requires a data.attributes wrapper for aggregate_spans.
    This function wraps the request and normalizes the response so commands
    can use a consistent interface: response.data.buckets[].computes/.by

    Args:
        client: DatadogClient instance
        filter_dict: {"query": ..., "from": ..., "to": ...}
        compute_list: [{"aggregation": ..., "metric": ...}]
        group_by_list: [{"facet": ...}] or None

    Returns:
        Response with .data.buckets[].computes/.by interface
    """
    attributes = {
        "filter": filter_dict,
        "compute": compute_list,
    }
    if group_by_list:
        attributes["group_by"] = group_by_list

    body = {
        "data": {
            "type": "aggregate_request",
            "attributes": attributes,
        }
    }

    response = client.spans.aggregate_spans(body=body)
    raw_data = response.data

    # Mock responses return .data.buckets (old format) — pass through as-is
    if hasattr(raw_data, "buckets"):
        return response

    # Real API returns .data as a list of SpansAggregateBucket
    raw_buckets = raw_data if isinstance(raw_data, list) else []

    class NormalizedBucket:
        def __init__(self, bucket):
            self.by = bucket.attributes.by
            self.computes = bucket.attributes.compute

    class NormalizedData:
        def __init__(self, buckets):
            self.buckets = buckets

    class NormalizedResponse:
        def __init__(self, buckets):
            self.data = NormalizedData(buckets)

    return NormalizedResponse([NormalizedBucket(b) for b in raw_buckets])
