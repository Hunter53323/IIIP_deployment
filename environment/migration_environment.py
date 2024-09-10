from environment.application import Application, Microservice
from environment.hardware import Server
from environment.moveable_device import Moveable_device, Production_hardware_with_moveable_device
from database import Database
from environment.base_environment import Running_time, Production_software
from algorithm.main_algorithm import Algorithm
import copy
import random
import time

class Prodution(Production_software, Production_hardware_with_moveable_device):
    """完整的生产环境，包括硬件和软件，数据库和算法，运行时间模块"""
    def __init__(self,database:Database, start_time:int = 0, end_time:int = 10, algorithm_type:str = "base", no_output:bool = False):
        self.running_time = Running_time(start_time, end_time)
        self.db = database
        self.config = None
        self.algorithm = Algorithm(database=self.db, algorithm_type=algorithm_type)
        Production_hardware_with_moveable_device.__init__(self, running_time = self.running_time, database=self.db)
        Production_software.__init__(self,database=self.db)
        self.no_output = no_output

    @property
    def current_time(self):
        """当前时间"""
        return self.running_time.current_time

    # ----------------------数据库存取部分----------------------

    def add_db_production_dynamic_before_action(self):
        """
        生产中的动态信息添加到数据库中
        当前数据库中拥有的信息：
        静态：微服务库，应用程序库，微服务数量，应用程序数量；设备库，服务器库，设备数量，服务器数量，服务器拓扑
        动态：设备与服务器的连接关系，设备请求的应用，微服务的部署情况
        """
        device_request_app = {}
        for device_id in self.device_library:
            device:Moveable_device = self.device_library[device_id]
            # 记录设备请求的应用
            device_request_app[device_id] = list(device.request_app_library.keys())
        self.db.add(t = self.running_time.current_time, type = "state", key = "device_request_app", value = device_request_app)

    def add_db_production_dynamic_after_action(self):
        # 三重字典，m,k,i=n
        microservice_deployment = {}
        for device_id in self.device_library:
            device:Moveable_device = self.device_library[device_id]
            device_deployment = {}
            for app_id in device.request_app_library:
                app:Application = device.request_app_library[app_id]
                app_deployment = {}
                for microservice_id in app.microservice_library:
                    microservice:Microservice = app.microservice_library[microservice_id]
                    if microservice.get_deployed_server_id() != None:
                        app_deployment[microservice_id] = microservice.get_deployed_server_id()
                device_deployment[app_id] = app_deployment
            microservice_deployment[device_id] = device_deployment
        self.db.add(t = self.running_time.current_time, type = "state", key = "microservice_deployment", value = microservice_deployment)

        # 不同时刻各个服务器上部署的微服务情况和层、空间情况
        server_microservice_deployment = {}
        server_deployed_layers = {}
        server_left_storage = {}
        server_left_computing = {}
        for server_id in self.server_library:
            server:Server = self.server_library[server_id]
            server_microservice_deployment[server_id] = copy.deepcopy(server.deployed_ms_library)
            server_deployed_layers[server_id] = copy.deepcopy(server.deployed_layers)
            server_left_storage[server_id] = copy.deepcopy(server.left_storage)
            server_left_computing[server_id] = copy.deepcopy(server.left_computing)
        self.db.add(t = self.running_time.current_time, type = "state", key = "server_microservice_deployment", value = server_microservice_deployment)
        self.db.add(t = self.running_time.current_time, type = "state", key = "server_deployed_layers", value = server_deployed_layers)
        self.db.add(t = self.running_time.current_time, type = "state", key = "server_left_storage", value = server_left_storage)
        self.db.add(t = self.running_time.current_time, type = "state", key = "server_left_computing", value = server_left_computing)

    def add_db_fixed(self):
        self.db.add_static_data(key = "migration_cost", value = self.config["migration_cost"])
        self.add_db_hardware()
        self.add_db_software()

    def add_db_dynamic_before_action(self):
        self.add_db_hardware_dynamic() #设备与服务器的连接关系
        self.add_db_production_dynamic_before_action()

    def add_db_dynamic_after_action(self):
        self.add_db_production_dynamic_after_action()

    # ----------------------微服务部署、卸载、迁移模块----------------------

    def deploy_microservice(self, device_id:int, application_id:int, microservice_id:int, server_id:int):
        """
        根据指定的m,k,i,将指定的微服务部署到指定的服务器上
        """
        microservice:Microservice = self.get_microservice_from_device_app_ms(device_id, application_id, microservice_id)
        if microservice.get_deployed_server_id() != None:
            raise ValueError("Microservice already deployed!")
        # TODO: 这里是只有部署微服务的考虑，要么改成微服务迁移要么就直接这么用
        server = self.find_server_from_id(server_id)

        if not server.deploy_ms(microservice):
            raise ValueError("Server not deploy!")

    def migrate_microservice(self, device_id:int, application_id:int, microservice_id:int, server_id:int):
        """
        根据指定的m,k,i,将指定的微服务从当前服务器迁移到指定的服务器上
        warning: 迁移使用整体迁移的方法，先全部卸载再全部迁移，该方法迁移单个微服务可以用，会被淘汰，使用migrate_microservices
        """
        microservice:Microservice = self.get_microservice_from_device_app_ms(device_id, application_id, microservice_id)
        if microservice.get_deployed_server_id() == None:
            raise ValueError("Microservice not deployed!")
        if microservice.get_deployed_server_id() == server_id:
            raise ValueError("Microservice already deployed on server!")
        
        last_server_id = microservice.get_deployed_server_id()
        last_server = self.find_server_from_id(last_server_id)
        last_server.undeploy_ms(microservice)

        server = self.find_server_from_id(server_id)
        if not server.deploy_ms(microservice):
            last_server.deploy_ms(microservice)
            raise ValueError("Not enough resources on server!")
        if not self.no_output:
            print("Microservice %d migrated from server %d to server %d" % (microservice_id, last_server_id, server_id))

    def migrate_microservices(self,migrate_action:dict):
        """
        微服务的批量卸载后进行迁移
        """
        app_dict:dict
        ms_dict:dict

        last_server_id = []
        for device_id, app_dict in migrate_action.items():
            for app_id, ms_dict in app_dict.items():
                for ms_id, server_id in ms_dict.items():
                    last_server_id.append(self.undeploy_microservice(device_id, app_id, ms_id))

        for device_id, app_dict in migrate_action.items():
            for app_id, ms_dict in app_dict.items():
                for ms_id, server_id in ms_dict.items():
                    self.deploy_microservice(device_id, app_id, ms_id, server_id)
                    if not self.no_output:
                        print("Microservice %d migrated from server %d to server %d" % (ms_id, last_server_id.pop(0), server_id))

    def undeploy_microservice(self, device_id:int, application_id:int, microservice_id:int):
        """
        根据指定的m,k,i,从服务器上移除指定的微服务
        """
        microservice:Microservice = self.get_microservice_from_device_app_ms(device_id, application_id, microservice_id)
        deployed_server_id = microservice.get_deployed_server_id()
        if deployed_server_id == None:
            raise ValueError("Microservice not deployed!")
        server = self.find_server_from_id(deployed_server_id)
        server.undeploy_ms(microservice)
        return deployed_server_id
    
    # ----------------------部署及预部署模块----------------------

    def deploy(self, action:dict):
        """
        根据action,执行服务器的部署策略
        action_dict有一个最上层的结构为{"deploy":{},"migrate":{},"undeploy":{}}
        里面的每一层都是{device_id:{application_id:{microservice_id:server_id}}}
        action中的策略即为最终需要进行部署的策略
        """
        app_dict:dict
        ms_dict:dict

        action_deploy:dict
        action_migrate:dict
        action_undeploy:dict

        if "deploy" in action:
            action_deploy = action["deploy"]
            for device_id, app_dict in action_deploy.items():
                for app_id, ms_dict in app_dict.items():
                    for ms_id, server_id in ms_dict.items():
                        self.deploy_microservice(device_id, app_id, ms_id, server_id)
        
        # if "migrate" in action:
        #     action_migrate = action["migrate"]
        #     for device_id, app_dict in action_migrate.items():
        #         for app_id, ms_dict in app_dict.items():
        #             for ms_id, server_id in ms_dict.items():
        #                 self.migrate_microservice(device_id, app_id, ms_id, server_id)

        if "migrate" in action:
            action_migrate = action["migrate"]
            self.migrate_microservices(action_migrate)

        if "undeploy" in action:
            action_undeploy = action["undeploy"]
            for device_id, app_dict in action_undeploy.items():
                for app_id, ms_dict in app_dict.items():
                    for ms_id in ms_dict:
                        self.undeploy_microservice(device_id, app_id, ms_id)

    def _deploy_start_device_connect(self, config):
        """
        用于在起始时刻进行设备连接方式的确定
        """
        for device_config in config:
            self.move_device(device_id = device_config["id"], server_id = device_config["connected_server_id"], output=False)
            self.request_application(device_id = device_config["id"], application_id = device_config["request_app_ids"])
        # check?

    def _solve_start_deployment(self):
        """
        用于在起始时刻进行具体的预部署,贪婪策略
        """
        device:Moveable_device
        app:Application
        ms:Microservice
        server:Server
        for device in self.device_library.values():
            for app in device.request_app_library.values():
                for ms in app.microservice_library.values():
                    if ms.get_deployed_server_id() == None:
                        deploy_flag = False
                        server_shuffle = list(self.server_library.values())
                        random.shuffle(server_shuffle)
                        # for server in self.server_library.values():
                        for server in server_shuffle:
                            if server.deploy_ms(ms):
                                deploy_flag = True
                                break
                        if not deploy_flag:
                            raise ValueError("No server can deploy microservice {} in application {} in device {}!".format(ms.id, app.app_id, device.id))

    def _deploy_start_deployment(self, config):
        """
        用于在起始时刻进行具体的预部署
        """
        for deploy_config in config:
            flag = self.deploy_microservice(device_id = deploy_config["device_id"], application_id = deploy_config["application_id"], microservice_id = deploy_config["microservice_id"], server_id = deploy_config["server_id"])
            if not flag:
                raise ValueError("Deploy error!")
            
    def _gurobi_start_deployment(self):
        """利用gurobi进行起始时刻的部署"""
        first_algorithm = Algorithm(database=self.db, algorithm_type="fullgurobi")
        first_algorithm.algorithm.output = False
        action = first_algorithm.algorithm.first_deploy()
        self.deploy(action)
        self.db.add_dict(t = self.current_time, type="action", data = action)

    def _greedy_start_deployment(self):
        """利用贪婪算法进行起始时刻的部署"""
        first_algorithm = Algorithm(database=self.db, algorithm_type="greedy")
        action = first_algorithm.algorithm.first_deploy()
        self.deploy(action)
        self.db.add_dict(t = self.current_time, type="action", data = action)

            
    # ----------------------根据配置文件进行的设备移动、服务请求----------------------
            
    def move_device_from_config(self, movement:dict):
        """
        根据movement,移动设备
        """
        if movement["type"] == "point":
            self.move_device_with_point(movement["point"], output = not self.no_output)
        else:
            raise ValueError("Movement type error!")
        
    def request_from_config(self, request:dict):
        """
        根据request,请求应用
        """
        if self.running_time.current_time in request.keys():
            for item in request[self.running_time.current_time]:
                self.request_application(item["device_id"], item["app_id"])

    # ----------------------杂项函数----------------------
            
    def request_application(self, device_id:int, application_id:list):
        """
        设备请求应用,没测试过是否可用，理论应该没啥问题
        """
        device:Moveable_device = self.device_library[device_id]
        device_request_apps_last = device.get_request_app_ids()
        for app_id in application_id:
            if app_id not in device_request_apps_last:
                app = copy.deepcopy(self.application_library[app_id])
                device.request_app(app)
        for app_id in device_request_apps_last:
            if app_id not in application_id:
                device.cancel_request_app(app_id)

    def get_microservice_from_device_app_ms(self, device_id:int, application_id:int, microservice_id:int):
        """
        从设备、应用程序、微服务id获取指定的微服务实例
        """
        device:Moveable_device = self.find_device_from_id(device_id)
        app:Application = device.get_request_app_from_id(application_id)
        if not app.ms_id_in_app(microservice_id):
            raise ValueError("Microservice id not in application!")
        microservice = app.get_ms_from_id(microservice_id)
        return microservice

    def check_deployment(self):
        """
        检查所有的微服务是否都部署在服务器上
        """
        device:Moveable_device
        app:Application
        for device in self.device_library.values():
            for app in device.request_app_library.values():
                if not app.check_deployment():
                    raise ValueError("Application {}  in device {} not deployed!".format(app.app_id, device.id))
        return True

    # ------------------------对外可以调用的函数模块------------------------

    # ------------------------生产环境创建---------------------

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

        self.add_db_fixed()

    # ------------------------生产环境预部署---------------------

    def deploy_start(self, config):
        """
        用于在起始时刻进行预部署
        """
        self._deploy_start_device_connect(config["device"])
        self.add_db_dynamic_before_action()

        if config["status"] == "running":
            self._deploy_start_deployment(config["deployment"])
        elif config["status"] == "solve":
            self._solve_start_deployment()
        elif config["status"] == "gurobi":
            self._gurobi_start_deployment()
        elif config["status"] == "greedy":
            self._greedy_start_deployment()
        else:
            raise ValueError("Environment status is error!")
        
        self.add_db_dynamic_after_action()

        self.check_deployment()

    # ------------------------生产环境展示---------------------

    def show(self):
        """
        展示当前的所有服务器上的微服务部署情况，目前使用文本进行输出
        """
        server:Server
        for server in self.server_library.values():
            print("Server {} deployed microservices:".format(server.id), server.deployed_ms_number)
            server.show_deployed_ms()

    def reset(self):
        """
        重置环境
        """
        # 对硬件进行重置
        device:Moveable_device
        server:Server
        self.db.reset()
        for device in self.device_library.values():
            device.reset()
        for server in self.server_library.values():
            server.reset()

        # 软件不需要进行重置，本身就是从软件库中取出的

        # 时间重置
        self.running_time.reset_time()

    def step(self,action:dict):
        """
        根据action,执行服务器的部署策略
        """
        # action里面要有一个部分是根据请求应用的情况进行新应用的部署或者是卸载，目前我们认为是请求的应用是不变的
        # self.running_time.print_time()
        # 这里有个问题，设备移动之后还没有添加到状态库里面，目前算法可能还拿不到数据，想一想如何处理
        # 下一步测试算法能否使用，进一步看一下实时的数据统计是不是对的
        self.deploy(action)
        self.check_deployment()
        
        self.add_db_dynamic_after_action()

    def time_next(self):
        """
        时间前进一步
        """
        if not self.running_time.next_time():
            return False
        return True

    def get_state(self):
        """
        获取当前的状态,并更新时间，若更新时间成功，返回True
        可以认为该模块是强化学习中的get observation
        """
        self.move_device_from_config(self.config["movement"])
        self.request_from_config(self.config["request"])
        # 某些数据统计以这个为分界线
        self.add_db_dynamic_before_action()

    def algorithm_solve(self, algorithm_used:Algorithm):
        """
        算法求解,求解完毕的动作会加入到数据库中
        求解集成在环境里面，也可以单独拆出来
        """
        start = time.perf_counter()

        algorithm_used.get_data(self.running_time.current_time)
        action = algorithm_used.solve()

        # self.algorithm.get_data(self.running_time.current_time)
        # action = self.algorithm.solve()

        end = time.perf_counter()
        self.db.add_dict(t = self.current_time, type="action", data = action)
        self.db.add(t = self.current_time, type="evaluate", key = "solve_time", value = end-start)

        return action
    
    # ------------------------动态信息的传递---------------------

    def get_movement(self, appointed_time_slot:int):
        """
        根据指定的时刻获得该时刻的移动和请求变化,特定于point的移动方式,当前是不包含请求的变化的
        """
        movement = {"type":"point","point":{appointed_time_slot:self.config["movement"]["point"][appointed_time_slot]}}
        return movement

    def get_state_with_input(self, movement, request):
        """
        根据外部输入进行系统参数的变化
        """
        self.move_device_from_config(movement)
        self.request_from_config(request)
        # 某些数据统计以这个为分界线
        self.add_db_dynamic_before_action()

    def get_deployment(self, appointed_time_slot:int):
        """
        根据指定的时刻获得该时刻的部署情况,格式为设备、应用、微服务部署在哪个服务器上
        """
        return self.db.get_state(appointed_time_slot)["microservice_deployment"]
        
    

