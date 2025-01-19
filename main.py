import asyncio
from aiohttp import web
from device_websocket import start_websocket_server
from phone_server import start_http_server
from headset_server import start_headset_server
from tasktracker import start_experiment

async def main():
    """
    主函数：同时启动 WebSocket 服务（设备和头显）和 HTTP 服务。
    """
    print("Starting all services...")

    # 启动 WebSocket 服务器（设备连接）
    websocket_server = await start_websocket_server()
    print("Device WebSocket server started on port 8765.")

    # 启动 HTTP 服务器（面向手机端）
    http_app = start_http_server()
    http_runner = web.AppRunner(http_app)
    await http_runner.setup()
    http_site = web.TCPSite(http_runner, "0.0.0.0", 8080)
    await http_site.start()
    print("HTTP server started on port 8080.")

    # 启动 WebSocket 服务器（头显连接）
    headset_app = start_headset_server()
    headset_runner = web.AppRunner(headset_app)
    await headset_runner.setup()
    headset_site = web.TCPSite(headset_runner, "0.0.0.0", 8766)
    await headset_site.start()
    print("Headset WebSocket server started on port 8766.")

    # 启动实验（记录开始时间）
    start_experiment()

    # 保持所有服务运行
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Shutting down...")
    finally:
        # 优雅地关闭 HTTP 和 WebSocket 服务
        await http_runner.cleanup()
        await headset_runner.cleanup()
        websocket_server.close()
        await websocket_server.wait_closed()
        print("All services stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped manually.")
