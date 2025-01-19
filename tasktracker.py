import json
import os
import asyncio
import datetime
from shared_data import device_states  # 获取设备当前状态
CORRECT_DEVICE = "Rectangle"
CORRECT_BRIGHTNESS = 80
CORRECT_COLOR = "Blue"


lock = asyncio.Lock()  # 线程安全锁
experiment_start_time = None  # 记录实验开始时间

# 任务列表
task_list = [
    {"id": 1, "name": "open_app", "status": "pending"},
    {"id": 2, "name": "add_device", "status": "pending"},
    {"id": 3, "name": "select_device", "status": "pending"},
    {"id": 4, "name": "enter_device", "status": "pending"},
    {"id": 5, "name": "control_device", "status": "pending"},
    {"id": 6, "name": "adjust_brightness", "status": "pending"},
    {"id": 7, "name": "change_color", "status": "pending"},
]

# 用户操作记录
user_actions = []

# ✅ 记录实验开始时间
def start_experiment():
    global experiment_start_time
    experiment_start_time = datetime.datetime.now()
    print(f"实验开始: {experiment_start_time.isoformat()}")

# ✅ 记录用户操作（带有时间戳）
async def record_user_action(task_name: str, actual_value):
    async with lock:
        action_record = {
            "task": task_name,
            "time": datetime.datetime.now().isoformat(),
            "value": actual_value
        }
        user_actions.append(action_record)
        print(f"记录操作: {action_record}")

async def check_task_1():
    await record_user_action("open_app", "WebSocket Connected")
    await update_task_status("open_app", "completed")

async def check_task_2():
    await record_user_action("add_device", "User clicked add device")
    await update_task_status("add_device", "completed")

async def check_task_3(selected_device: str):
    await record_user_action("select_device", selected_device)

    if selected_device == CORRECT_DEVICE:
        await update_task_status("select_device", "completed")
        print(f"任务 3 完成: 正确选择了设备 {selected_device}")
    else:
        print(f"任务 3 失败: 选择了错误设备 {selected_device}")

async def check_task_4(selected_device: str):
    await record_user_action("enter_device", selected_device)

    if selected_device == CORRECT_DEVICE:
        await update_task_status("enter_device", "completed")
        print(f"任务 4 完成: 正确进入设备 {selected_device}")
    else:
        print(f"任务 4 失败: 进入了错误设备 {selected_device}")

# ✅ 简化检测逻辑
async def check_tasks_5_to_7(device_name: str, actual_brightness: int, actual_color: str):
    """
    统一检测任务 5、6、7 的逻辑。
    """
    if device_name != CORRECT_DEVICE:
        print(f"错误的设备: {device_name}")
        return

    # 检测任务 5: 检查设备是否开启
    if actual_color != "off":
        await update_task_status("control_device", "completed")
        print(f"任务 5 完成: {device_name} 开关开启")
    else:
        await update_task_status("control_device", "pending")
        print(f"任务 5 重置为 pending: {device_name} 开关关闭")

    # 检测任务 6: 检查亮度
    if actual_brightness == CORRECT_BRIGHTNESS:
        await update_task_status("adjust_brightness", "completed")
        print(f"任务 6 完成: {device_name} 亮度正确 ({actual_brightness})")
    else:
        await update_task_status("adjust_brightness", "pending")
        print(f"任务 6 重置为 pending: {device_name} 亮度错误 ({actual_brightness})")

    # 检测任务 7: 检查颜色
    if actual_color == CORRECT_COLOR:
        await update_task_status("change_color", "completed")
        print(f"任务 7 完成: {device_name} 颜色正确 ({actual_color})")
    else:
        await update_task_status("change_color", "pending")
        print(f"任务 7 重置为 pending: {device_name} 颜色错误 ({actual_color})")

# ✅ 更新任务状态
async def update_task_status(task_name: str, new_status: str):
    async with lock:
        for task in task_list:
            if task["name"] == task_name:
                task["status"] = new_status
                print(f"任务状态更新: {task_name} -> {new_status}")


async def update_task_status(task_name: str, new_status: str):
    """
    更新任务状态，并推送更新到 WebSocket 客户端。
    """
    async with lock:
        for task in task_list:
            if task["name"] == task_name:
                task["status"] = new_status
                print(f"任务状态更新: {task_name} -> {new_status}")

                # 动态导入以避免循环依赖
                from headset_server import push_task_list
                await push_task_list()
def get_task_list():
    """
    获取当前的任务列表。
    """
    return task_list

