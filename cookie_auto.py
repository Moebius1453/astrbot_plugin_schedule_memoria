import json

import requests
import websocket

DEBUG_PORT = 9222
HOST_FILTER = "wuyiu"


def get_cookies() -> str:
    """通过 Edge 调试端口（CDP）获取教务 cookie。Edge 未开调试模式时抛 ConnectionError"""
    try:
        ver = requests.get(
            f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=3
        ).json()
    except Exception as e:
        raise ConnectionError(
            f"无法连接 Edge 调试端口（{DEBUG_PORT}）。"
            "请关闭所有 Edge 窗口后用调试模式重新启动：\n"
            'msedge.exe --remote-debugging-port=9222\n'
            "（或修改 Edge 快捷方式，在目标后追加该参数）"
        ) from e

    ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=10)
    ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
    resp = json.loads(ws.recv())
    ws.close()

    cookies = resp.get("result", {}).get("cookies", [])
    parts = [
        f"{c['name']}={c['value']}"
        for c in cookies
        if HOST_FILTER in c.get("domain", "")
    ]
    if not parts:
        raise ConnectionError(
            "调试端口已连接，但浏览器里没有教务（wuyiu）的 cookie——请先在 Edge 中登录教务系统"
        )
    return "; ".join(parts)
