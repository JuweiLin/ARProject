#notifier.py
import asyncio
from asyncio import Lock
import copy
from tasktracker import check_task_1

lock = Lock()
websocket_clients = set()  # 用于存储前端 WebSocket 客户端
last_notified_device_states = {}  # 用于存储上次推送的设备状态

# 通知所有 WebSocket 客户端设备状态更新
async def notify_websocket_clients(device_states, full_update=False):
    """
    通知 WebSocket 客户端设备状态更新。
    :param device_states: 当前的设备状态字典
    :param full_update: 是否发送完整状态更新
    """
    global last_notified_device_states

    updates = []
    if full_update:
        # 如果是完整更新，直接发送所有设备的状态
        updates = [
            {
                "device_name": name,
                "status": state.get("status", "offline"),
                "brightness": state.get("brightness", 0),
                "color": state.get("color", "off"),
            }
            for name, state in device_states.items()
        ]
        last_notified_device_states = copy.deepcopy(device_states)  # 使用深拷贝
        print("[Debug] Full update: All device states sent.")
    else:
        # 检测设备状态变化
        for name, state in device_states.items():
            last_state = last_notified_device_states.get(name, {})

            # 检测状态变化或新增设备
            if (
                state.get("status") != last_state.get("status") or
                state.get("brightness") != last_state.get("brightness") or
                state.get("color", "").lower() != last_state.get("color", "").lower()
            ):
                updates.append({
                    "device_name": name,
                    "status": state.get("status", "offline"),
                    "brightness": state.get("brightness", 0),
                    "color": state.get("color", "off"),
                })
                last_notified_device_states[name] = copy.deepcopy(state)
                print(f"[Debug] State change detected for '{name}': {state}")

        # 检测已移除的设备
        for name in set(last_notified_device_states.keys()) - set(device_states.keys()):
            updates.append({
                "device_name": name,
                "status": "offline",
                "brightness": 0,
                "color": "off",
            })
            print(f"[Debug] Removed device detected: {name}")
            del last_notified_device_states[name]

    if not updates and not full_update:
        print("[Debug] No state changes detected. Skipping notification.")
        return

    # 确保未变化的设备也包含在通知中
    if not full_update:
        for name in device_states.keys():
            if name not in [update["device_name"] for update in updates]:
                updates.append({
                    "device_name": name,
                    "status": device_states[name].get("status", "offline"),
                    "brightness": device_states[name].get("brightness", 0),
                    "color": device_states[name].get("color", "off"),
                })

    message = {"type": "device_update", "data": updates}

    async with lock:
        for client in list(websocket_clients):
            try:
                await client.send_json(message)
                print(f"[Debug] Notification sent to client: {message}")
            except Exception as e:
                print(f"[Error] Failed to notify WebSocket client: {e}")
                websocket_clients.discard(client)



# WebSocket 路由处理函数
async def websocket_handler(request):
    """
    处理 WebSocket 客户端的连接。
    """
    from aiohttp import web, WSMsgType
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async with lock:
        websocket_clients.add(ws)

    print("[Debug] WebSocket client connected.")
    await check_task_1()

    # 在客户端连接时，发送完整的设备状态
    from shared_data import device_states  # 确保能访问最新设备状态
    await notify_websocket_clients(device_states, full_update=True)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                print(f"[Debug] Received from WebSocket client: {msg.data}")
            elif msg.type == WSMsgType.ERROR:
                print(f"[Error] WebSocket connection error: {ws.exception()}")
    except Exception as e:
        print(f"[Error] WebSocket error: {e}")
    finally:
        async with lock:
            websocket_clients.discard(ws)
        print("[Debug] WebSocket client disconnected.")
    return ws
