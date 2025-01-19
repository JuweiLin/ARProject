from aiohttp import web
import aiohttp_cors
from device_websocket import send_command_to_device
from notifier import websocket_handler, notify_websocket_clients
from shared_data import connected_clients, device_states
from asyncio import Lock
from tasktracker import check_task_2, check_task_3, check_task_4

lock = Lock()  # 确保全局线程安全的锁

# 设备列表路由
async def get_device_list(request):
    """
    Returns the list of currently connected devices with their states.
    """
    async with lock:  # 确保线程安全地访问 `connected_clients` 和 `device_states`
        device_list = [
            {
                "device_name": name,
                "status": device_states[name]["status"],
                "brightness": device_states[name]["brightness"],
                "color": device_states[name]["color"],
            }
            for name in connected_clients.keys()
        ]
    return web.json_response({"devices": device_list})

# 命令路由
async def handle_command(request):
    try:
        data = await request.json()
        device_name = data.get("device")
        command = data.get("command")

        if not device_name or not command:
            return web.json_response({"status": "error", "message": "Missing 'device' or 'command'."}, status=400)

        result = await send_command_to_device(device_name, command)
        if result.startswith("Error"):
            return web.json_response({"status": "error", "message": result}, status=400)

        return web.json_response({"status": "success", "message": result}, status=200)

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# 设备上线路由
async def set_device_online(request):
    try:
        data = await request.json()  # 获取 POST 请求的 JSON 数据
        device_name = data.get("device_name")

        if not device_name:
            return web.json_response({"status": "error", "message": "Missing 'device_name'."}, status=400)

        async with lock:  # 确保线程安全
            if device_name in device_states:
                # 更新设备状态为 online
                device_states[device_name]["status"] = "online"
                print(f"Device '{device_name}' is now online.")

                await check_task_3(device_name)

                # 通知 WebSocket 客户端设备状态变化
                await notify_websocket_clients(device_states)

                return web.json_response({"status": "success", "message": f"Device '{device_name}' is now online."}, status=200)
            else:
                return web.json_response({"status": "error", "message": f"Device '{device_name}' not found."}, status=404)

    except Exception as e:
        print(f"Error in set_device_online: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)
 
async def add_device_detector(request):
    try:
        await check_task_2()

        return web.json_response({"status": "success", "message": "Task 2 (Add Device) completed."}, status=200)

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def enter_device(request):
    """
    用户点击设备，进入设备 UI 时，触发任务 4 记录。
    """
    try:
        data = await request.json()
        device_name = data.get("device_name")

        if not device_name:
            return web.json_response({"status": "error", "message": "Missing 'device_name'."}, status=400)

        # ✅ 任务 4 记录 (检测是否进入正确设备)
        await check_task_4(device_name)

        return web.json_response({"status": "success", "message": f"User entered device '{device_name}'."}, status=200)

    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# 启动 HTTP 服务
def start_http_server():
    app = web.Application()

    # 设置路由
    app.router.add_get("/devices", get_device_list)
    app.router.add_post("/command", handle_command)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_post("/set_device_online", set_device_online)
    app.router.add_post("/add_device_detector", add_device_detector)
    app.router.add_post("/enter_device", enter_device)

    # 配置 CORS 支持
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)

    return app
