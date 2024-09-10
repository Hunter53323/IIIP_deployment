from database import Database
from environment.moveable_device import Moveable_device
from environment.application import Application,Microservice
from environment.hardware import Server
import networkx as nx
from environment.base_environment import Running_time

class Evaluate():
    """
    功能是评估迁移成本、镜像拉取成本和通讯开销，给出基础函数就可以
    整个评估函数里面没有考虑请求app情况的变化
    """
    def __init__(self, database:Database):
        self.database = database

    # ------------------------可以调用的评估函数------------------------

    def evaluate_migration_cost(self, time:int):
        """微服务迁移成本"""
        return self.migration_cost(time)

    def evaluate_image_pull_cost(self, time:int):
        """微服务镜像拉取成本"""
        return self.image_pull_cost(time)
    
    def evaluate_communication_cost(self, time:int):
        """部署策略执行后的微服务通讯成本"""
        return self.communication_cost(time)
    
    def evaluate_communication_cost_after_move(self, time:int):
        """设备移动后、部署策略执行前的通讯成本"""
        return self.communication_cost_after_move(time)
    
    def evaluate_production(self, time:int, theta_1:float, theta_2:float, theta_3:float):
        """
        评估迁移、新服务下载、通讯差距
        # 评估函数为：theta_1 * 迁移成本 + theta_2 * 新服务下载成本 + theta_3 * 通讯成本
        """
        result = theta_1 * self.evaluate_migration_cost(time) + theta_2 * self.evaluate_image_pull_cost(time) + theta_3 * self.evaluate_communication_cost(time)
        self.database.add(t = time, type= "evaluate", key = "production", value = result)
        return result
    
    # ------------------------内部函数------------------------

    def migration_cost(self, time:int):
        """
        迁移成本,当前没有考虑服务请求发生变化的情况下的部署和关闭情况
        """
        device_set:dict = self.database.static_data["device_library"]
        device:Moveable_device
        app:Application
        cost = 0
        for device_id, device in device_set.items():
            for app_id, app in device.request_app_library.items():
                for ms_id, _ in app.microservice_library.items():
                    cost += self._microservice_migration_cost(time, device_id, app_id, ms_id)
        self.database.add(t = time, type= "evaluate", key = "migration_cost", value = cost)
        return cost

    def _microservice_migration_cost(self, time:int, device_id:int, application_id:int, microservice_id:int):
        """
        根据时间，设备，应用，微服务，计算迁移成本
        """
        last_deploy_server_id = self._get_microservice_deployment_server(time-1, device_id, application_id, microservice_id)
        current_deploy_server_id = self._get_microservice_deployment_server(time, device_id, application_id, microservice_id)
        if last_deploy_server_id == current_deploy_server_id:
            return 0
        else:
            return self._get_microservice_migration_cost(microservice_id, current_deploy_server_id)

    def _get_microservice_migration_cost(self, microservice_id:int, server_id:int):
        """
        访问得到迁移成本，没有任何判断，不对外开放使用
        """
        # 基础数据，迁移到服务器i的成本，微服务i的部署位置和上一时刻部署位置
        for i in self.database.static_data["migration_cost"]:
            if i["microservice_id"] == microservice_id and i["server_id"] == server_id:
                return i["cost"]
            
    def _get_microservice_deployment_server(self, time:int, device_id:int, application_id:int, microservice_id:int):
        """
        获取微服务部署的服务器
        """
        if time in self.database.data.keys():
            deployment = self.database.data[time]["state"]["microservice_deployment"]
        else:
            raise ValueError("Time error!")
        return deployment[device_id][application_id][microservice_id]
            
    def image_pull_cost(self, time:int):
        """
        镜像拉取成本,当前没有考虑服务请求发生变化的情况下的部署和关闭情况
        """
        device_set:dict = self.database.static_data["device_library"]
        device:Moveable_device
        app:Application
        cost = 0
        for device_id, device in device_set.items():
            for app_id, app in device.request_app_library.items():
                for ms_id, ms in app.microservice_library.items():
                    cost += self._get_image_pull_cost(time, device_id, app_id, ms_id)
        self.database.add(t = time, type= "evaluate", key = "image_pull_cost", value = cost)
        return cost

    def _get_image_pull_cost(self, time:int, device_id:int, application_id:int, microservice_id:int):
        """
        获取镜像拉取成本
        """
        last_deploy_server_id = self._get_microservice_deployment_server(time-1, device_id, application_id, microservice_id)
        current_deploy_server_id = self._get_microservice_deployment_server(time, device_id, application_id, microservice_id)
        if last_deploy_server_id == current_deploy_server_id:
            return 0
        else:
            return self._get_image_pull_cost_from_server(time,microservice_id,current_deploy_server_id)

    def _get_image_pull_cost_from_server(self, time:int, microservice_id:int, server_id:int):
        """
        获取镜像拉取成本
        """
        last_layers:dict = self._get_server_layers(time-1, server_id)
        microservice:Microservice = self.database.static_data["microservice_library"][microservice_id]
        ms_layers = microservice.layers
        pull_layer = 0
        for layer_name, layer_size in ms_layers.items():
            if layer_name in last_layers.keys():
                pass
            else:
                pull_layer += layer_size
        server:Server = self.database.static_data["server_library"][server_id]
        server_bandwidth = server.bandwidth
        return pull_layer/server_bandwidth

    def _get_server_layers(self, time:int, server_id:int):
        """
        获取服务器上的镜像层
        """
        if time in self.database.data.keys():
            layers = self.database.data[time]["state"]["server_deployed_layers"]
        else:
            raise ValueError("Time error!")
        return layers[server_id]

    def communication_cost(self, time:int):
        """
        通讯开销的计算
        """
        device_set:dict = self.database.static_data["device_library"]
        device:Moveable_device
        total_cost = 0
        for device_id,device in device_set.items():
            for app_id in device.request_app_library.keys():
                total_cost += self.communication_of_application(time, device_id, app_id)
        self.database.add(t = time, type= "evaluate", key = "communication_cost", value = total_cost)
        return total_cost

    def communication_of_application(self, time:int, device_id:int, application_id:int):
        """
        计算应用的通讯开销
        """
        #TODO: 设备连接到的服务器目前是只看时刻t的，但是实际的通讯开销需要看移动前后的通讯开销变化，因此需要有新的函数做到这一点
        device:Moveable_device = self.database.static_data["device_library"][device_id]
        app:Application = device.request_app_library[application_id]
        # device_server_id = device.connected_server_id
        device_server_id = self.database.data[time]["state"]["device_connect_to_server"][device_id]
        head_id = app.find_head()
        ms_deployed_server_id = self._get_microservice_deployment_server(time, device_id, application_id, head_id)
        hop = self._get_hops_of_two_server(device_server_id, ms_deployed_server_id)
        # 这里为什么hop不加1，这是因为服务请求发送到服务器必然会存在一跳的开销，这个开销时无法避免的，当然也可以通过+1变成真实的开销
        cost = hop * app.source_message["data"] + self._calculate_communication(time, device_id, application_id, head_id)
        return cost
    
    def communication_cost_after_move(self, time:int):
        """
        通讯开销的计算
        """
        device_set:dict = self.database.static_data["device_library"]
        device:Moveable_device
        total_cost = 0
        for device_id,device in device_set.items():
            for app_id in device.request_app_library.keys():
                total_cost += self.communication_of_application_after_move(time, device_id, app_id)
        self.database.add(t = time, type= "evaluate", key = "communication_cost_after_move", value = total_cost)
        return total_cost

    def communication_of_application_after_move(self, time:int, device_id:int, application_id:int):
        """
        计算应用的通讯开销
        """
        #TODO: 设备的连接服务器是当前时刻的，但是部署情况是上一时刻的部署情况
        device:Moveable_device = self.database.static_data["device_library"][device_id]
        app:Application = device.request_app_library[application_id]
        # device_server_id = device.connected_server_id
        device_server_id = self.database.data[time]["state"]["device_connect_to_server"][device_id]
        head_id = app.find_head()
        ms_deployed_server_id = self._get_microservice_deployment_server(time-1, device_id, application_id, head_id)
        hop = self._get_hops_of_two_server(device_server_id, ms_deployed_server_id)
        # 这里为什么hop不加1，这是因为服务请求发送到服务器必然会存在一跳的开销，这个开销时无法避免的
        cost = hop * app.source_message["data"] + self._calculate_communication(time-1, device_id, application_id, head_id)
        return cost
    
    def _calculate_communication(self, time:int, device_id:int, application_id:int, microservice_id_1:int):
        """
        计算两个微服务之间的通讯开销
        """
        device:Moveable_device = self.database.static_data["device_library"][device_id]
        application:Application = device.request_app_library[application_id]
        microservice_1:Microservice = application.microservice_library[microservice_id_1]
        cost = 0
        for next_ms in microservice_1.next_ms:
            cost += self._calculate_communication_of_two_micriservice(time, device_id, application_id, microservice_1.id, next_ms)
            cost += self._calculate_communication(time, device_id, application_id, next_ms)
        return cost

    def _calculate_communication_of_two_micriservice(self, time:int, device_id:int, application_id:int, microservice_id_1:int, microservice_id_2:int):
        """
        计算任意两个微服务间的通讯开销
        """
        server_id_1 = self._get_microservice_deployment_server(time, device_id, application_id, microservice_id_1)
        server_id_2 = self._get_microservice_deployment_server(time, device_id, application_id, microservice_id_2)
        hop = self._get_hops_of_two_server(server_id_1, server_id_2)
        communication = self._get_data_of_two_micriservice(application_id, microservice_id_1, microservice_id_2)
        return hop * communication
    
    def _get_data_of_two_micriservice(self, application_id:int, microservice_id_1:int, microservice_id_2:int):
        """
        获得两个微服务间的通讯数据量
        """
        application:Application = self.database.static_data["application_library"][application_id]
        return application.get_data_from_message(microservice_id_1, microservice_id_2)
        
    def _get_hops_of_two_server(self, server_id_1:int, server_id_2:int):
        """
        获取两个服务器之间的跳数
        """
        G = self.database.static_data["topo"]
        return nx.shortest_path_length(G, source = server_id_1, target = server_id_2)
