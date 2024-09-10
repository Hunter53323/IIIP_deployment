# 从hardware中的device改善而来，用于将固定的设备改写为可移动的生产设备
from environment.hardware import Server, Device
from database import Database
from environment.base_environment import Running_time, Production_hardware
import random, copy

class Moveable_device(Device):
    """
    可移动的设备，增加了设备的连接时间
    """
    def __init__(self, id:int, connected_server_id:int):
        super().__init__(id = id, connected_server_id = connected_server_id)
        self.connected_time = 0

class Production_hardware_with_moveable_device(Production_hardware):
    """
    设备可移动的自定义环境
    """
    def __init__(self, running_time:Running_time, database:Database):
        super().__init__(database=database)
        self.running_time = running_time
        self.db = database

    def add_db_hardware_dynamic(self):
        """
        不同时刻设备和服务器的连接情况
        """
        device_connected_to_server = {}
        for device_id in self.device_library:
            device:Moveable_device = self.device_library[device_id]
            server_id = device.connected_server_id
            device_connected_to_server[device_id] = server_id
        self.db.add(t = self.running_time.current_time, type = "state", key = "device_connect_to_server", value = device_connected_to_server)

        server_connect_to_device = {}
        for server_id in self.server_library:
            server:Server = self.server_library[server_id]
            server_connect_to_device[server_id] = server.connected_devices_id
        self.db.add(t = self.running_time.current_time, type = "state", key = "server_connect_to_device", value = server_connect_to_device)

    def add_config_to_device_library(self, config:list):
        """
        重写父类的方法，添加可移动设备
        """
        for device_config in config:
            self._add_config_to_device_library(id = device_config["id"], config = device_config)

    def _add_config_to_device_library(self, id:int, config:dict):
        """
        重写父类的方法，添加可移动设备
        """
        # config 包括 id, connected_server
        self.device_library[id] = Moveable_device(id = id, connected_server_id = config["connected_server_id"])
        self.device_number += 1
        if config["connected_server_id"] == None:
            return
        server:Server = self.find_server_from_id(config["connected_server_id"])
        server.add_device(id)

    def find_device_from_id(self, id:int):
        """
        重写父类的方法，添加可移动设备
        """
        device:Moveable_device = self.device_library[id]
        return device
    
    # ------------------------设备移动相关函数------------------------
    
    def move_device(self, device_id:int, server_id:int, output:bool = True):
        device = self.find_device_from_id(device_id)
        server = self.find_server_from_id(server_id)
        if device_id not in self.device_library:
            raise ValueError("Device id not in library!")
        if server_id not in self.server_library:
            raise ValueError("Server id not in library!")
        if device.connected_server_id == server_id:
            if output:
                print("Device %d already in the server %d !" % (device_id, server_id))
            return False
        if device.connected_server_id == None:
            device.move_to_other_server(server_id)
            server.add_device(device_id)
            device.connected_time = self.running_time.current_time
            if output:
                print("Device %d is connected to server %d!" % (device_id, server_id))
            return True
        # 删除原服务器的设备
        ori_server_id = device.connected_server_id
        ori_server = self.find_server_from_id(ori_server_id)
        ori_server.remove_device(device_id)
        # 移动并更新服务器的设备列表
        device.move_to_other_server(server_id)
        server.add_device(device_id)
        # 更新设备的连接时间
        device.connected_time = self.running_time.current_time
        if output:
            print("Move device %d from server %d to server %d at time %d" % (device_id, ori_server_id, server_id, self.running_time.current_time))
        return True

    # ------------------------不同的设备移动规则------------------------

    def random_move_device(self):
        """随机选择一个设备，随机选择一个服务器进行随机移动"""
        device_id = random.choice(list(self.device_library.keys()))
        server_id = random.choice(list(self.server_library.keys()))
        self.move_device(device_id, server_id)

    def move_device_with_rule(self, rule:dict):
        """
        根据概率进行设备的移动,rule为二重字典，第一重key为设备id，第二重key为服务器id，value为移动概率
        """
        for device_id in rule:
            server_id_list = list(rule[device_id].keys())
            prob_list = list(rule[device_id].values())
            server_id = random.choices(server_id_list, weights = prob_list, k = 1)[0]
            self.move_device(device_id, server_id)

    def move_device_with_path(self, path:dict):
        """
        根据某种移动规则进行设备的移动,rule为二重字典，第一重key为设备id，第二重key为移动时间间隔列表和服务器id列表
        time_interval:[3,6,2,4,6], server_id:[1,2,3,4,5]，表示在第3个时间间隔后移动到服务器1，再过6个时间间隔后移动到服务器2，以此类推
        """
        for device_id in path:
            current_server_id = self.device_library[device_id].connected_server
            try:
                current_server_id_index = path[device_id]["server_id"].index(current_server_id)
            except ValueError:
                # 当前服务器不在路径中，直接移动到第一个服务器
                self.move_device(device_id, path[device_id]["server_id"][0])
            current_time_interval = self.running_time.current_time - self.device_library[device_id].connected_time
            if current_time_interval > path[device_id]["time_interval"][current_server_id_index]:
                # 当前时间间隔大于路径中的时间间隔，移动到下一个服务器
                server_id = path[device_id]["server_id"][current_server_id_index + 1]
                self.move_device(device_id, server_id)
    
    def move_device_with_point(self, rule:dict, output:bool = True):
        """
        给定时刻、设备id、设备连接到的服务器，每个时刻根据这三个数值来确定设备的位置
        最上层是一个time为key的字典，每个字典内都是一个list，list内的每个元素都是一个字典，字典内包含device_id和server_id
        """
        if self.running_time.current_time not in rule.keys():
            return
        time_rule:list = copy.copy(rule[self.running_time.current_time])
        for movement in time_rule:
            device_id = movement["device_id"]
            server_id = movement["server_id"]
            if not self.move_device(device_id, server_id, output = output):
                # 设备已经在目标服务器上，不需要移动
                time_rule.remove(movement)
        self.db.add(t= self.running_time.current_time, type="state", key="movement", value=time_rule)

    # ------------------------获取设备到服务器的跳数------------------------

    def get_device_server_hop(self, device_id:int, server_id:int):
        """
        获取设备和服务器之间的跳数
        """
        device_server_id = self.device_library[device_id].connected_server
        return self.topo_get_hop(device_server_id, server_id)
    
    def get_server_server_hop(self, server_id_1:int, server_id_2:int):
        """
        获取服务器和服务器之间的跳数
        """
        return self.topo_get_hop(server_id_1, server_id_2)
    
    # 还可以获取设备到服务器的通讯路径，可以自行实现