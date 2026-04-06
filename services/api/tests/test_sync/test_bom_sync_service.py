import httpx

from app.sync.bom_sync_service import classify_bom_sync_exception


class TestClassifyBomSyncException:
    def test_http_500_is_transient(self):
        exc = httpx.HTTPStatusError("err", request=httpx.Request("GET", "http://x"), response=httpx.Response(500))
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"

    def test_http_429_is_transient(self):
        exc = httpx.HTTPStatusError("err", request=httpx.Request("GET", "http://x"), response=httpx.Response(429))
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"

    def test_http_404_is_permanent(self):
        exc = httpx.HTTPStatusError("err", request=httpx.Request("GET", "http://x"), response=httpx.Response(404))
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "permanent_error"

    def test_timeout_is_transient(self):
        exc = httpx.ReadTimeout("timed out")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"

    def test_connect_error_is_transient(self):
        exc = httpx.ConnectError("connection refused")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"

    def test_sap_bom_runtime_error_is_permanent(self):
        exc = RuntimeError("SAP BOM error: material not found")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "permanent_error"

    def test_value_error_is_permanent(self):
        exc = ValueError("invalid data format")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "permanent_error"

    def test_unknown_exception_is_permanent(self):
        exc = Exception("something unexpected")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "permanent_error"

    def test_connection_error_is_transient(self):
        exc = ConnectionError("connection reset")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"

    def test_os_error_is_transient(self):
        exc = OSError("network unreachable")
        kind, _ = classify_bom_sync_exception(exc)
        assert kind == "transient_error"
