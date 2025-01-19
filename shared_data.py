#shared_data.py
# 用于存储 WebSocket 连接和设备状态的共享数据

# 连接的设备字典：键是设备名称，值是 WebSocket 对象
connected_clients = {}

# 存储设备状态的字典：键是设备名称，值是设备状态
device_states = {}
