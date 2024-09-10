# 工业微服务部署系统的参数配置文件
CONFIG_ENVIRONMENT = {
    # 系统基本参数配置文件
    "device": [
        # {"id": 1, "connected_server_id": None},
        # {"id": 2, "connected_server_id": None},
        # {"id": 3, "connected_server_id": None},
        # {"id": 4, "connected_server_id": None},
        {"id": 1, "connected_server_id": None},
        {"id": 2, "connected_server_id": None},
        {"id": 3, "connected_server_id": None},
        {"id": 4, "connected_server_id": None},
        {"id": 5, "connected_server_id": None},
    ],
    "server": [  # 算力单位:GFlopS, 带宽单位:Gbps, 存储单位:GBG
        {"id": 1, "computing": 30, "storage": 32, "bandwidth": 0.1},
        {"id": 2, "computing": 30, "storage": 32, "bandwidth": 0.1},
        {"id": 3, "computing": 30, "storage": 32, "bandwidth": 0.1},
        {"id": 4, "computing": 30, "storage": 32, "bandwidth": 0.1},
    ],
    "topo": [  # 边缘服务器的网络拓扑
        {"server_1": 1, "server_2": 2},
        {"server_1": 1, "server_2": 3},
        {"server_1": 1, "server_2": 4},
        {"server_1": 2, "server_2": 3},
    ],
    "application": [  # data单位为KB，sender和receiver为对应的微服务id
        {"id": 1, "name": "app_1", "ms_id_list": [1, 2], "message": [{"data": 101, "sender": 1, "receiver": 2}], "source_message_data": 101},
        {
            "id": 2,
            "name": "app_2",
            "ms_id_list": [3, 4, 5],
            "message": [{"data": 102, "sender": 3, "receiver": 4}, {"data": 103, "sender": 4, "receiver": 5}],
            "source_message_data": 102,
        },
        {
            "id": 3,
            "name": "app_3",
            "ms_id_list": [3, 7, 8],
            "message": [{"data": 104, "sender": 3, "receiver": 7}, {"data": 105, "sender": 7, "receiver": 8}],
            "source_message_data": 103,
        },
        {"id": 4, "name": "app_4", "ms_id_list": [6, 7], "message": [{"data": 106, "sender": 6, "receiver": 7}], "source_message_data": 104},
        {"id": 5, "name": "app_5", "ms_id_list": [1, 7], "message": [{"data": 107, "sender": 1, "receiver": 7}], "source_message_data": 105},
    ],
    "microservice": [  # 层单位GB
        {"id": 1, "layers": {"layer1": 0.3}, "cpu": 5, "name": "microservice_1"},
        {"id": 2, "layers": {"layer2": 0.4}, "cpu": 3, "name": "microservice_2"},
        {"id": 3, "layers": {"layer3": 0.5}, "cpu": 2, "name": "microservice_3"},
        {"id": 4, "layers": {"layer4": 0.8}, "cpu": 10, "name": "microservice_4"},
        {"id": 5, "layers": {"layer5": 1.2}, "cpu": 1, "name": "microservice_5"},
        {"id": 6, "layers": {"layer6": 1.8}, "cpu": 4, "name": "microservice_6"},
        {"id": 7, "layers": {"layer7": 0.9}, "cpu": 2, "name": "microservice_7"},
        {"id": 8, "layers": {"layer8": 0.2}, "cpu": 5, "name": "microservice_8"},
    ],
    # 动态环境中的参数配置文件
    "movement": {
        "type": "point",  # "point" or "line
        "point": {  # key为时刻，value为每个时刻的设备id和设备连接到的服务器id list
            1: [{"device_id": 1, "server_id": 3}],
            3: [{"device_id": 1, "server_id": 1}],
        },
        "random": {},
        "path": {},
    },
    "request": {  # key为时刻，value为每个时刻的设备id和设备请求的应用id list，如果没有出现设备那么就沿用上次，如果出现了那么就更新为新的请求应用
        # 2: [{"device_id":1, "app_id":3}],
        # 4: [{"device_id":1, "app_id":4}],
    },
    # 初始时刻的参数配置文件
    "start": {  # 用于决定系统的起始是从什么条件开始，是从硬件分配完成后就直接开始，还是要做动态的研究，因此从某一个中间状态开始？
        "status": "running",  # "runing" or "init"
        "device": [  # 设备在起始时的连接情况
            {"id": 1, "connected_server_id": 1, "request_app_ids": [2, 4]},
            {"id": 2, "connected_server_id": 2, "request_app_ids": [3]},
            {"id": 3, "connected_server_id": 3, "request_app_ids": [1]},
            {"id": 4, "connected_server_id": 4, "request_app_ids": [4]},
            {"id": 5, "connected_server_id": 2, "request_app_ids": [5]},
        ],
        "deployment": [  # 微服务在起始时的部署情况
            {"device_id": 1, "application_id": 2, "microservice_id": 3, "server_id": 3},
            {"device_id": 1, "application_id": 2, "microservice_id": 4, "server_id": 4},
            {"device_id": 1, "application_id": 2, "microservice_id": 5, "server_id": 4},
            {"device_id": 1, "application_id": 4, "microservice_id": 6, "server_id": 2},
            {"device_id": 1, "application_id": 4, "microservice_id": 7, "server_id": 2},
            {"device_id": 2, "application_id": 3, "microservice_id": 3, "server_id": 3},
            {"device_id": 2, "application_id": 3, "microservice_id": 7, "server_id": 3},
            {"device_id": 2, "application_id": 3, "microservice_id": 8, "server_id": 2},
            {"device_id": 3, "application_id": 1, "microservice_id": 1, "server_id": 1},
            {"device_id": 3, "application_id": 1, "microservice_id": 2, "server_id": 2},
            {"device_id": 4, "application_id": 4, "microservice_id": 6, "server_id": 4},
            {"device_id": 4, "application_id": 4, "microservice_id": 7, "server_id": 4},
            {"device_id": 5, "application_id": 5, "microservice_id": 1, "server_id": 2},
            {"device_id": 5, "application_id": 5, "microservice_id": 7, "server_id": 2},
        ],
    },  # 起始部署、起始链接、起始请求
    # 数据分析中会用到的配置参数
    "migration_cost": [  # 迁移的成本，微服务i迁移到服务器j的成本
        {"microservice_id": 1, "server_id": 1, "cost": 0.21},
        {"microservice_id": 1, "server_id": 2, "cost": 0.22},
        {"microservice_id": 1, "server_id": 3, "cost": 0.23},
        {"microservice_id": 1, "server_id": 4, "cost": 0.24},
        {"microservice_id": 2, "server_id": 1, "cost": 0.25},
        {"microservice_id": 2, "server_id": 2, "cost": 0.26},
        {"microservice_id": 2, "server_id": 3, "cost": 0.27},
        {"microservice_id": 2, "server_id": 4, "cost": 0.28},
        {"microservice_id": 3, "server_id": 1, "cost": 0.29},
        {"microservice_id": 3, "server_id": 2, "cost": 0.30},
        {"microservice_id": 3, "server_id": 3, "cost": 0.31},
        {"microservice_id": 3, "server_id": 4, "cost": 0.32},
        {"microservice_id": 4, "server_id": 1, "cost": 0.33},
        {"microservice_id": 4, "server_id": 2, "cost": 0.34},
        {"microservice_id": 4, "server_id": 3, "cost": 0.35},
        {"microservice_id": 4, "server_id": 4, "cost": 0.36},
        {"microservice_id": 5, "server_id": 1, "cost": 0.37},
        {"microservice_id": 5, "server_id": 2, "cost": 0.38},
        {"microservice_id": 5, "server_id": 3, "cost": 0.39},
        {"microservice_id": 5, "server_id": 4, "cost": 0.40},
        {"microservice_id": 6, "server_id": 1, "cost": 0.41},
        {"microservice_id": 6, "server_id": 2, "cost": 0.42},
        {"microservice_id": 6, "server_id": 3, "cost": 0.43},
        {"microservice_id": 6, "server_id": 4, "cost": 0.44},
        {"microservice_id": 7, "server_id": 1, "cost": 0.45},
        {"microservice_id": 7, "server_id": 2, "cost": 0.46},
        {"microservice_id": 7, "server_id": 3, "cost": 0.47},
        {"microservice_id": 7, "server_id": 4, "cost": 0.48},
        {"microservice_id": 8, "server_id": 1, "cost": 0.49},
        {"microservice_id": 8, "server_id": 2, "cost": 0.50},
        {"microservice_id": 8, "server_id": 3, "cost": 0.51},
        {"microservice_id": 8, "server_id": 4, "cost": 0.52},
    ],
}
import random


class ConfigGenerate:
    """
    配置文件生成模块，当前没有请求变化的情况，只有设备移动
    """

    def __init__(
        self,
        seed: int = 0,
        device_number: int = 15,
        server_number: int = 9,
        application_number: int = 15,
        microservice_number: int = 30,
        start_mode: str = "running",
        end_time: int = 40,
    ):
        self.config = {}
        random.seed(seed)

        self.device_number = device_number
        self.server_number = server_number
        self.application_number = application_number
        self.microservice_number = microservice_number

        self.application = None
        self.start_mode = start_mode  # running, solve
        self.end_time = end_time

    def generate(self):
        """生成配置文件"""
        self.config["device"] = self.generate_device()
        self.config["server"] = self.generate_server()
        self.config["topo"] = self.generate_topology()
        self.config["microservice"] = self.generate_microservice()
        self.config["application"] = self.generate_application()
        self.config["movement"] = self.generate_movement()
        self.config["request"] = self.generate_request()
        self.config["start"] = self.generate_start()
        self.config["migration_cost"] = self.generate_migration_cost()
        return self.config

    def generate_device(self):
        """生成设备，属性有设备id和连接的服务器id，默认连接服务器为None"""
        device = []
        for i in range(self.device_number):
            device.append({"id": i + 1, "connected_server_id": None})
        return device

    def generate_server(self, rand_attr=False):
        """生成服务器，属性有服务器id，计算能力，存储空间，带宽"""
        if rand_attr:
            # 这里的随机不是每次都随机
            computing = random.randint(100, 200)
            storage = random.randint(16, 48)
            bandwidth = random.randrange(0.1, 0.5, 0.1)
        else:
            # 服务器计算能力和存储空间
            # computing = 40 # 110
            # storage = 16 # 32
            # bandwidth = 0.1
            computing = 110  # 110
            storage = 32  # 32
            bandwidth = 0.1
        server = []
        for i in range(self.server_number):
            server.append({"id": i + 1, "computing": computing, "storage": storage, "bandwidth": bandwidth})
        return server

    def generate_topology(self):
        """生成拓扑，拓扑属性为边缘服务器之间的链接关系"""
        topo = []
        for i in range(self.server_number - 1):
            topo.append({"server_1": i + 1, "server_2": i + 2})

        candidate_topo = []
        for i in range(self.server_number - 1):
            for j in range(i + 2, self.server_number):
                candidate_topo.append({"server_1": i + 1, "server_2": j + 1})
        topo += random.sample(candidate_topo, random.randint(0, len(candidate_topo)))
        return topo

    def generate_microservice(self):
        """
        生成微服务，微服务属性有微服务id，所包含的层，占用的cpu算力，微服务名称
        目前的配置是只生成一个layer，后续可以扩展
        "microservice": [ # 层单位GB
        {"id": 1, "layers": {"layer1":0.3}, "cpu": 5, "name": "microservice_1"},
        """
        microservice = []
        for i in range(self.microservice_number):
            microservice_dict = {}
            microservice_dict["id"] = i + 1
            layer_str = "layer" + str(i + 1)
            microservice_dict["layers"] = {layer_str: random.randint(1, 10) / 5}
            microservice_dict["cpu"] = random.randint(1, 10)
            microservice_dict["name"] = "microservice_" + str(i + 1)
            microservice.append(microservice_dict)
        return microservice

    def generate_application(self):
        """生成应用程序，属性包括id，名称，包含的微服务id列表，消息列表，源消息数据"""
        application = []
        for i in range(self.application_number):
            application_dict = {}
            application_dict["id"] = i + 1
            application_dict["name"] = "app_" + str(i + 1)
            application_dict["ms_id_list"] = random.sample(range(1, self.microservice_number), random.randint(2, 4))
            application_dict["message"] = []
            for j in range(len(application_dict["ms_id_list"]) - 1):
                application_dict["message"].append(
                    {"data": random.randint(50, 500), "sender": application_dict["ms_id_list"][j], "receiver": application_dict["ms_id_list"][j + 1]}
                )
            application_dict["source_message_data"] = random.randint(50, 500)
            application.append(application_dict)
        self.application = application
        return application

    def generate_movement(self):
        """
        生成设备的移动特征，point表示在某个时间点设备几移动到某个服务器，random表示在某个时间段内随机移动到某个服务器，不用写配置文件，path表示在某个时间段内按照某个路径循环移动，具体移动规则可参阅moveable_device中的Production_hardware_with_moveable_device里面的不同移动规则介绍
        一次只移动一个设备
        """
        movement = {}
        movement["type"] = "point"
        movement["point"] = {}
        movement["random"] = {}
        movement["path"] = {}
        # movement_time_list = random.sample(range(1, 15), random.randint(3, 7))
        movement_time_list = list(range(1, self.end_time + 1))
        movement_time_list.sort()
        for i in range(len(movement_time_list)):
            # move_number = 1
            move_number = random.randint(1, 6)
            move_devices = random.sample(range(1, self.device_number + 1), move_number)
            move_servers = [random.randint(1, self.server_number) for _ in range(move_number)]
            # movement['point'][movement_time_list[i]] = [{"device_id": random.randint(1, self.device_number), "server_id": random.randint(1, self.server_number)}]
            move_list = []
            for j in range(move_number):
                move_list.append({"device_id": move_devices[j], "server_id": move_servers[j]})
            movement["point"][movement_time_list[i]] = move_list
        return movement

    def generate_request(self):
        """
        在不同时刻设备产生不同的服务请求，下面为每个时刻的样例，时刻，设备id，请求的服务ids
        # 4: [{"device_id":1, "app_id":[1,4]}],
        """
        return {}

    def generate_start(self):
        """生成初始时候的配置，包括设备的初始位置，初始部署的应用等，根据不同的start_mode生成方式也不同，可以根据已有的方法（gurobi，贪婪）生成，也可以随机生成，start_mode代表初始的部署方案，solve代表初始的时候随机选取一个部署，gurobi代表初始的时候使用fullgurobi求解一个部署方案，running代表从配置文件里面读取，只有deployment是可以根据start_mode不从配置文件里面走，别的都是从配置文件读取的"""
        if self.application == None:
            raise Exception("application is None")
        start = {}
        start["status"] = self.start_mode
        start["device"] = []
        for i in range(self.device_number):
            device_dict = {}
            device_dict["id"] = i + 1
            device_dict["connected_server_id"] = random.randint(1, self.server_number)
            device_dict["request_app_ids"] = [random.randint(1, self.application_number)]
            start["device"].append(device_dict)
        start["deployment"] = []
        for device in start["device"]:
            for app in device["request_app_ids"]:
                for a in self.application:
                    if a["id"] == app:
                        for ms in a["ms_id_list"]:
                            deployment_dict = {}
                            deployment_dict["device_id"] = device["id"]
                            deployment_dict["application_id"] = app
                            deployment_dict["microservice_id"] = ms
                            # 这里的两个分别代表随机部署微服务和按照设备的连接情况部署微服务
                            deployment_dict["server_id"] = random.randint(1, self.server_number)
                            # deployment_dict['server_id'] = device['connected_server_id']
                            start["deployment"].append(deployment_dict)
        return start

    def generate_migration_cost(self):
        """
        迁移的成本，微服务i迁移到服务器j的成本
        """
        migration_cost = []
        for i in range(self.microservice_number):
            for j in range(self.server_number):
                migration_cost_dict = {}
                migration_cost_dict["microservice_id"] = i + 1
                migration_cost_dict["server_id"] = j + 1
                migration_cost_dict["cost"] = random.random()
                migration_cost.append(migration_cost_dict)
        return migration_cost


def get_config(
    seed: int = 0,
    device_number: int = 15,
    server_number: int = 9,
    application_number: int = 15,
    microservice_number: int = 30,
    start_mode: str = "running",
    end_time: int = 40,
):
    """
    生成配置文件
    """
    config_f = ConfigGenerate(seed, device_number, server_number, application_number, microservice_number, start_mode, end_time)
    return config_f.generate()


if __name__ == "__main__":
    config_f = ConfigGenerate()
    C = config_f.generate()
    print(C)
