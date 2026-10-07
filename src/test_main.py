import json

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_ping(client: TestClient):
    response = client.get("/ping")
    assert response.status_code == 200

    response = client.get("/")
    assert response.status_code == 200


def test_mcp_initialize_list_tools_and_call_local_endpoint(client: TestClient):
    headers = {"Accept": "application/json, text/event-stream"}
    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "proxy-tool-tests", "version": "1.0"},
            },
        },
    )
    assert response.status_code == 200, response.text
    initialized = response.json()["result"]
    assert initialized["capabilities"]["tools"] is not None
    headers["mcp-session-id"] = response.headers["mcp-session-id"]
    headers["mcp-protocol-version"] = initialized["protocolVersion"]

    response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert response.status_code == 202, response.text

    response = client.post(
        "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    assert response.status_code == 200, response.text
    tool_name = app.openapi()["paths"]["/api/basic/whoami"]["post"]["operationId"][:64]
    assert any(tool["name"] == tool_name for tool in response.json()["result"]["tools"])

    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": {}},
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert not result.get("isError"), result
    assert json.loads(result["content"][0]["text"])["path"] == "/api/basic/whoami"
