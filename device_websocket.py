import asyncio
import websockets
from shared_data import connected_clients, device_states
from asyncio import Lock
from notifier import notify_websocket_clients
from tasktracker import check_tasks_5_to_7

lock = Lock()  # 全局锁，确保字典安全更新

# WebSocket 事件处理
async def handler(websocket, path):
    device_name = None
    try:
        print("New device attempting to connect...")
        # 等待设备发送其名称
        device_name = await websocket.recv()
        if not device_name.startswith("DEVICE_NAME:"):
            print(f"Invalid registration message: {device_name}")
            await websocket.close()
            return

        device_name = device_name.split(":", 1)[1].strip()
        client_ip = websocket.remote_address[0]

        async with lock:  # 线程安全地更新设备列表
            connected_clients[device_name] = websocket
            device_states[device_name] = {
                "status": "offline",
                "brightness": 0,
                "color": "off",
            }
        print(f"Device '{device_name}' connected with IP: {client_ip}")

        # 通知 WebSocket 客户端新设备已连接
        await notify_websocket_clients(device_states)

        # 监听消息并发送心跳
        while True:
            pong_task = None
            try:
                await asyncio.sleep(5)  # 每隔 1 秒发送一次心跳
                print(f"Sending PING to {device_name}...")
                await websocket.send("PING")  # 主动发送 PING 消息

                # 等待设备的消息（包括状态更新或 PONG 响应）
                pong_task = asyncio.create_task(websocket.recv())
                done, pending = await asyncio.wait([pong_task], timeout=5)

                if pong_task in done:
                    response = pong_task.result()
                    if response.startswith("STATUS:"):
                        # 解析设备状态
                        await process_device_status(device_name, response)
                    else:
                        print(f"Unexpected response from '{device_name}': {response}")
                else:
                    print(f"Device '{device_name}' unresponsive. Disconnecting...")
                    break

            except websockets.exceptions.ConnectionClosedOK:
                print(f"Device '{device_name}' closed connection gracefully.")
                break
            except asyncio.TimeoutError:
                print(f"Device '{device_name}' timed out. Disconnecting...")
                break
            except Exception as e:
                print(f"Unexpected error for '{device_name}': {e}")
                break
            finally:
                # 清理未完成的任务
                if pong_task:
                    pong_task.cancel()
                    try:
                        await pong_task
                    except asyncio.CancelledError:
                        pass

    except websockets.exceptions.ConnectionClosed:
        print(f"Device '{device_name}' disconnected.")
    finally:
        # 清理断开的设备
        async with lock:
            if device_name in connected_clients:
                del connected_clients[device_name]
            if device_name in device_states:
                del device_states[device_name]
        await notify_websocket_clients(device_states)
        print(f"Cleaned up resources for '{device_name}'.")

# 处理设备状态更新
async def process_device_status(device_name, response):
    try:
        print(f"Processing status update from '{device_name}': {response}")
        status_data = response[len("STATUS:"):].split(",")
        brightness = None
        color = None

        for item in status_data:
            key, value = item.split("=")
            key = key.strip()
            value = value.strip()
            if key == "brightness":
                brightness = int(value)
            elif key == "color":
                color = value

        if brightness is not None and color is not None:
            async with lock:
                device_states[device_name]["brightness"] = brightness
                device_states[device_name]["color"] = color
            print(f"Updated state for '{device_name}': {device_states[device_name]}")
            await notify_websocket_clients(device_states)  # 推送更新到 WebSocket 客户端
        else:
            print(f"Incomplete status data from '{device_name}': {response}")
    except Exception as e:
        print(f"Error parsing STATUS from '{device_name}': {e}")

# 向指定设备发送命令
async def send_command_to_device(device_name, command):
    """
    Sends a command to a specific connected device and updates its state proactively.

    :param device_name: Name of the target device
    :param command: Command to send to the device
    :return: A status message
    """
    async with lock:
        if device_name not in connected_clients:
            return f"Error: Device '{device_name}' not connected."

        try:
            # 发送命令到设备
            await connected_clients[device_name].send(command)
            print(f"Command '{command}' sent to '{device_name}'")

            # 模拟主动状态更新
            # 解析命令并更新设备状态
            brightness, color = parse_command(command)
            device_states[device_name]["brightness"] = brightness
            device_states[device_name]["color"] = color

            print(f"Updated state for '{device_name}': {device_states[device_name]}")
            
            await check_tasks_5_to_7(device_name, brightness, color)
            # 通知前端状态变化
            await notify_websocket_clients(device_states)

            return f"Success: Command '{command}' sent to '{device_name}'."
        except websockets.exceptions.ConnectionClosed:
            print(f"Failed to send command. Device '{device_name}' disconnected.")
            del connected_clients[device_name]
            del device_states[device_name]
            return f"Error: Failed to send command. Device '{device_name}' disconnected."
            
def parse_command(command):
    """
    Parses the command string and extracts brightness and color.

    :param command: Command string in the format "COLOR BRIGHTNESS".
    :return: (brightness, color) tuple.
    """
    try:
        parts = command.split()
        if len(parts) == 2:
            color = parts[0]
            brightness = int(parts[1])
            return brightness, color
    except Exception as e:
        print(f"[Error] Failed to parse command: {e}")
    # 如果解析失败，返回默认值
    return 0, "off"



# 启动 WebSocket 服务
async def start_websocket_server():
    print("Starting WebSocket server...")
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        8765,
    )
    return server
