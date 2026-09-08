from __future__ import annotations

import http.client
from http.server import ThreadingHTTPServer
from threading import Thread

from quaestio.research import ResearchStore
from quaestio.research_view import handler_for


def test_view_reads_current_study_and_serves_retained_evidence(tmp_path):
    database = tmp_path / "study.sqlite"
    with ResearchStore.create(database, title="Viewer study") as store:
        node = store.create_node(kind="question", title="Question", content="", actor="test", operation_id="q")
        attachment = store.attach_artifact(node["id"], data=b"evidence", label="Observation",
                                            actor="test", operation_id="evidence")
    with ThreadingHTTPServer(("127.0.0.1", 0), handler_for(database)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            assert response.status == 200
            assert response.getheader("Cache-Control") == "no-store"
            assert b"Viewer study" in response.read()
            connection.request("GET", "/api/artifacts/" + attachment["id"])
            response = connection.getresponse()
            assert response.status == 200
            assert response.getheader("Content-Disposition").startswith("attachment;")
            assert response.read() == b"evidence"
            connection.request("POST", "/api/graph", body=b"{}")
            response = connection.getresponse()
            assert response.status == 501
            response.read()
            connection.request("GET", "/api/graph", headers={"Host": "example.test"})
            response = connection.getresponse()
            assert response.status == 403
            response.read()
        finally:
            connection.close()
            server.shutdown()
            thread.join(timeout=5)
    with ResearchStore(database) as store:
        assert store.snapshot()["cursor"] == 2
