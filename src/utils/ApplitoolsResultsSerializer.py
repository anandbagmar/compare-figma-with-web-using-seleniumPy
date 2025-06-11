# src/utils/results_serializer.py

from applitools.common import TestResults

def serialize_test_results(results: TestResults) -> dict:
    return {
        "name": results.name,
        "app_name": results.app_name,
        "status": str(results.status),  # fix for TestResultsStatus
        "url": results.url,
        "is_new": results.is_new,
        "is_different": results.is_different,
        "is_aborted": results.is_aborted,
        "host_display_size": {
            "width": results.host_display_size.width,
            "height": results.host_display_size.height
        } if results.host_display_size else None,
        "matches": results.matches,
        "mismatches": results.mismatches,
        "missing": results.missing,
    }
