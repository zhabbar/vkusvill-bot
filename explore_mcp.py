import json
import requests

MCP_URL = "https://mcp.vkusvill.ru/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def parse_response(r):
    """MCP может отвечать обычным JSON или SSE. Умеем и то, и другое."""
    text = r.text.strip()
    if text.startswith("event:") or "\ndata:" in text or text.startswith("data:"):
        # SSE-формат: ищем строки, начинающиеся с "data:"
        for line in text.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    continue
        return {"raw_sse": text[:2000]}
    try:
        return r.json()
    except json.JSONDecodeError:
        return {"raw": text[:2000]}


def mcp_call(session_id, method, params=None, req_id=2):
    headers = dict(HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    r = requests.post(MCP_URL, json=payload, headers=headers, timeout=60)
    return r, parse_response(r)


def main():
    # 1. Инициализация
    print("=== 1. initialize ===")
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "explore", "version": "1.0"},
        },
    }
    r = requests.post(MCP_URL, json=init_payload, headers=HEADERS, timeout=60)
    print("HTTP status:", r.status_code)
    print("Server headers:")
    for k, v in r.headers.items():
        if k.lower() in ("mcp-session-id", "content-type", "server", "date"):
            print(f"  {k}: {v}")
    parsed = parse_response(r)
    print("Body:", json.dumps(parsed, ensure_ascii=False, indent=2)[:2000])

    session_id = r.headers.get("mcp-session-id")
    print("\nSession id:", session_id)

    # 2. notifications/initialized (без ответа)
    if session_id:
        print("\n=== 2. notifications/initialized ===")
        notify = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        headers = dict(HEADERS)
        headers["mcp-session-id"] = session_id
        rn = requests.post(MCP_URL, json=notify, headers=headers, timeout=30)
        print("HTTP status:", rn.status_code, "(no body expected)")

    # 3. tools/list
    print("\n=== 3. tools/list ===")
    rt, parsed_tools = mcp_call(session_id, "tools/list", {}, req_id=2)
    print("HTTP status:", rt.status_code)
    print("Body:", json.dumps(parsed_tools, ensure_ascii=False, indent=2)[:5000])


if __name__ == "__main__":
    main()