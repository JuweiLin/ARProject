import asyncio
from aiohttp import web, WSMsgType

# 保存与头显的 WebSocket 连接
headset_clients = set()
lock = asyncio.Lock()  # 线程安全锁

async def push_task_list():
    """
    将任务列表推送给所有已连接的头显客户端。
    """
    from tasktracker import get_task_list  # 动态导入，避免循环依赖
    task_list = get_task_list()  # 获取任务列表

    if not headset_clients:
        print("[Info] No headset connected. Skipping push.")
        return

    message = {"type": "task_update", "data": task_list}
    async with lock:
        disconnected_clients = []
        for ws in headset_clients:
            try:
                await ws.send_json(message)
                print(f"[Info] Task list pushed to headset: {message}")
            except Exception as e:
                print(f"[Error] Failed to send task list to headset: {e}")
                disconnected_clients.append(ws)

        # 移除断开的客户端
        for ws in disconnected_clients:
            headset_clients.discard(ws)
            print("[Info] Disconnected headset removed.")

async def websocket_handler(request):
    """
    处理头显客户端的 WebSocket 连接。
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async with lock:
        headset_clients.add(ws)
    print("[Info] Headset connected.")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                print(f"[Info] Received from headset: {msg.data}")
            elif msg.type == WSMsgType.ERROR:
                print(f"[Error] WebSocket error: {ws.exception()}")
    except Exception as e:
        print(f"[Error] WebSocket connection error: {e}")
    finally:
        async with lock:
            headset_clients.discard(ws)
        print("[Info] Headset disconnected.")
    return ws

def start_headset_server():
    """
    启动头显 WebSocket 服务器。
    """
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)  # WebSocket 路径
    return app
