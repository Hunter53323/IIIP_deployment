# 基础环境包括参数的基本定义，和强化学习环境差不多
from environment.application import Application, Microservice, Message
from environment.hardware import Server, Device
from database import Database
import copy
import networkx as nx
import matplotlib.pyplot as plt
import random

class Running_time:
    """
    运行时间模块
    """
    def __init__(self, start_time:int = 0, end_time:int = 9999):
        self._start_time = start_time
        self._current_time = start_time
        self._end_time = end_time

    def next_time(self):
        """时间运行"""
        self._current_time += 1
        if self._current_time > self._end_time:
            self._current_time -= 1
            return False
        return True
    
    @property
    def current_time(self):
        return self._current_time
    
    def reset_time(self):
        """重置时间"""
        self._current_time = self._start_time

    def print_time(self):
        print(f"Current time: {self._current_time}")

class Production_hardware:
    """
    结合服务器和设备的硬件生产环境，构建统一的网络拓扑
    """
    def __init__(self, database:Database):
        self.server_library = {}
        self.device_library = {}

        self.server_number = 0
        self.device_number = 0

        self.G = nx.Graph()
        self.db = database

    def add_db_hardware(self):
        """数据库存储"""
        self.db.add_static_data(key = "server_library", value = self.server_library)
        self.db.add_static_data(key = "device_library", value = self.device_library)
        self.db.add_static_data(key = "server_number", value = self.server_number)
        self.db.add_static_data(key = "device_number", value = self.device_number)
        self.db.add_static_data(key = "topo", value = self.G)

    # 根据配置文件进行环境创建

    def add_config_to_server_library(self, config:list):
        for server_config in config:
            self._add_config_to_server_library(id = server_config["id"], config = server_config)

    def _add_config_to_server_library(self, id:int, config:dict):
        # config 包括 storage, computing, bandwidth
        self.server_library[id] = Server(id = id, storage = config["storage"], computing = config["computing"], bandwidth = config["bandwidth"])
        self.server_number += 1

    def add_config_to_device_library(self, config:list):
        for device_config in config:
            self._add_config_to_device_library(id = device_config["id"], config = device_config)

    def _add_config_to_device_library(self, id:int, config:dict):
        # config 包括 id, connected_server
        self.device_library[id] = Device(id = id, connected_server_id = config["connected_server_id"])
        self.device_number += 1

    def find_server_from_id(self, id:int):
        """根据id查找服务器"""
        try:
            server:Server = self.server_library[id]
            return server
        except:
            raise Exception("Server id not found")
    
    def find_device_from_id(self, id:int):
        """根据id查找设备"""
        try:
            device:Device = self.device_library[id]
            return device
        except:
            raise Exception("Device id not found")

    # 网络拓扑模块
    def add_topo(self, config:list):
        """根据配置文件添加网络拓扑"""
        self.topo_add_node()
        self.topo_add_edge(config)

    def topo_add_node(self):
        """添加节点"""
        for key in self.server_library:
            self.G.add_node(key)

    def topo_add_edge(self, config:list):
        """添加边"""
        for edge in config:
            self.G.add_edge(edge["server_1"], edge["server_2"])

    def topo_get_hop(self, server_id_1:int, server_id_2:int):
        """获取两个服务器之间的跳数"""
        return nx.shortest_path_length(self.G, source = server_id_1, target = server_id_2)
    
    def show_hardware(self):
        """
        展示当前的服务器和设备的连接情况，可以用nx进行呈现
        """

        # 创建服务器网络拓扑图G
        show_G = copy.deepcopy(self.G)
        devices = []

        server:Server
        for server in self.server_library.values():
            for device_id in server.connected_devices_id:
                show_G.add_edge(server.id, device_id+100)  # 设备的编号加100，避免和服务器的编号重复
                devices.append(device_id+100)

        # 绘制图形
        pos = nx.spring_layout(show_G) # 设置节点位置
        options = {"node_size": 500, "alpha": 0.8} # 设置节点选项
        nx.draw_networkx_nodes(show_G, pos, nodelist=self.server_library.keys(), node_color="r", **options) # 绘制服务器节点，颜色为红色
        nx.draw_networkx_nodes(show_G, pos, nodelist=devices, node_color="y", **options) # 绘制设备节点，颜色为蓝色
        nx.draw_networkx_edges(show_G, pos, width=1.0) # 绘制边
        nx.draw_networkx_labels(show_G, pos) # 绘制节点标签
        plt.axis("off") # 关闭坐标轴
        plt.show() # 显示图形
    
class Production_software:
    """
    结合应用程序和微服务的软件生产环境
    """
    def __init__(self, database:Database):
        self.microservice_library = {}
        self.application_library = {}

        self.microservice_number = 0
        self.application_number = 0

        self.db = database

    def add_db_software(self):
        """数据库存储"""
        self.db.add_static_data(key = "microservice_library", value = self.microservice_library)
        self.db.add_static_data(key = "application_library", value = self.application_library)
        self.db.add_static_data(key = "microservice_number", value = self.microservice_number)
        self.db.add_static_data(key = "application_number", value = self.application_number)

    # 根据配置文件设置生产环境参数
    def add_config_to_microservice_library(self, config:list):
        for microservice_config in config:
            self._add_config_to_microservice_library(id = microservice_config["id"], config = microservice_config)
    
    def _add_config_to_microservice_library(self, id:int, config:dict):
        # config 包括 layers, cpu, name
        self.microservice_library[id] = Microservice(id = id, layers = config["layers"], cpu = config["cpu"], name = config["name"])
        self.microservice_number += 1

    def add_config_to_application_library(self, config:list):
        for application_config in config:
            self._add_config_to_application_library(id = application_config["id"], config = application_config)
        
    def _add_config_to_application_library(self, id:int, config:dict):
        # config 包括 name, app_id, ms_id_list(为包括的微服务id列表), message(为消息二元列表，data,sender,receiver)
        self.check_microservice_library(config["ms_id_list"])
        candidate_app = Application(name = config["name"], app_id = config["id"])

        ms_list = []
        for ms_id in config["ms_id_list"]:
            ms_list.append(copy.deepcopy(self.microservice_library[ms_id]))
        candidate_app.add_microservices(ms_list)

        message_list = []
        for message in config["message"]:
            message_list.append(Message(data = message["data"], sender = message["sender"], receiver = message["receiver"]))
        candidate_app.add_messages(message_list)

        source_msssage = config["source_message_data"]
        candidate_app.add_source_message(source_msssage)

        self.application_library[id] = candidate_app
        self.application_number += 1

    def check_microservice_library(self, ms_id_list:list):
        """检查微服务库中是否包含所有的微服务id"""
        for ms_id in ms_id_list:
            if ms_id not in self.microservice_library:
                raise ValueError("Microservice id not in library!")
            
    def show_software(self):
        """
        展示当前的软件环境，用文本来进行输出
        """
        # 该输出流的呈现只考虑了微服务链为线性的情况
        application:Application
        for application in self.application_library.values():
            print("app_id:", application.app_id, end=" Microservice: ")
            head_id = application.find_head()
            ms:Microservice = application.microservice_library[head_id]
            while ms.next_ms != []:
                print(ms.id, "->", end="")
                ms:Microservice = application.microservice_library[ms.next_ms[0]]
            print(ms.id)

class base_Prodution(Production_software, Production_hardware):
    """基础生产环境，包括硬件和软件，数据库和算法，运行时间模块"""
    def __init__(self,database:Database, start_time:int = 0, end_time:int = 10):
        self.running_time = Running_time(start_time, end_time)
        self.db = database
        self.config = None
        Production_hardware.__init__(self,database=self.db)
        Production_software.__init__(self,database=self.db)

    @property
    def current_time(self):
        """当前时间"""
        return self.running_time.current_time
    
    def create_environment_from_config(self, config:dict):
        """
        从配置文件里面创建生产环境,环境创建有顺序要求，先服务器再设备，再微服务再应用
        """
        self.add_config_to_server_library(config["server"])
        self.add_config_to_device_library(config["device"])
        self.add_topo(config["topo"])
        # 先添加微服务再添加应用，这个顺序不能变
        self.add_config_to_microservice_library(config["microservice"])
        self.add_config_to_application_library(config["application"])
        self.config = config

        self.add_db_hardware()
        self.add_db_software()

    def random_deploy(self):
        """随机部署"""
        application:Application
        for application in self.application_library.values():
            for ms in application.microservice_library.values():
                self.random_deploy_ms(ms)

    def random_deploy_ms(self, ms:Microservice):
        """随机部署一个微服务"""
        server_id = random.choice(list(self.server_library.keys()))
        server:Server = self.server_library[server_id]
        server.deploy_ms(ms)

    def show(self):
        """
        展示当前的所有服务器上的微服务部署情况，目前使用文本进行输出
        """
        server:Server
        for server in self.server_library.values():
            print("Server {} deployed microservices:".format(server.id), server.deployed_ms_number)
            server.show_deployed_ms()