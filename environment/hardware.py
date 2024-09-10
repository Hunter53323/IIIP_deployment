#服务器和生产设备基类
from environment.application import Microservice, Application
# from application import Microservice, Application
class Server:
    def __init__(self, id:int, storage:float, computing:float, bandwidth:float):
        # 存储空间
        self.storage = storage
        # 计算能力
        self.computing = computing
        # 与云服务器带宽
        self.bandwidth = bandwidth
        # 服务器id
        self.id = id

        self.left_storage = storage
        self.left_computing = computing

        self.deployed_layers = {}
        self.deployed_ms_library = {}
        self.deployed_ms_number = 0

        self.connected_devices_id = []

    def reset(self):
        self.left_storage = self.storage
        self.left_computing = self.computing
        self.deployed_layers = {}
        self.deployed_ms_library = {}
        self.connected_devices_id = []
        self.deployed_ms_number = 0

    def add_device(self, device_id:int):
        self.connected_devices_id.append(device_id)

    def remove_device(self, device_id:int):
        self.connected_devices_id.remove(device_id)

    def feasibility_of_deploy(self, ms:Microservice):
        """判断是否可以部署微服务"""
        # 判断是否已经部署过该微服务
        deployed_ms:Microservice
        if ms.subordinate_device in self.deployed_ms_library.keys():
            if ms.subordinate_app in self.deployed_ms_library[ms.subordinate_device].keys():
                for deployed_ms in self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app].values():
                    if ms.id == deployed_ms.id:
                        raise ValueError("Microservice m,k,i already deployed!")
        # 判断是否有足够的存储空间
        occupy_storage = 0
        for key in ms.layers.keys():
            if key not in self.deployed_layers.keys():
                occupy_storage += ms.layers[key]
        # round是因为浮点数计算的误差
        if occupy_storage > round(self.left_storage,2):
            # raise ValueError("Not enough storage!")
            return False
        # 判断是否有足够的计算能力
        if ms.cpu > round(self.left_computing,2):
            # raise ValueError("Not enough computing power!")
            return False
        return True

    def deploy_ms(self, ms:Microservice):
        """部署微服务,更新剩余容量"""
        if self.feasibility_of_deploy(ms):
            if ms.subordinate_device not in self.deployed_ms_library.keys():
                self.deployed_ms_library[ms.subordinate_device] = {}
                self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app] = {}
            elif ms.subordinate_app not in self.deployed_ms_library[ms.subordinate_device].keys():
                    self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app] = {}
            self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app][ms.id] = ms
            # 对层去重
            occupy_storage = 0
            for key in ms.layers.keys():
                if key not in self.deployed_layers.keys():
                    self.deployed_layers[key] = 1
                    occupy_storage += ms.layers[key]
                else:
                    self.deployed_layers[key] += 1
            self.left_storage -= occupy_storage
            self.left_computing -= ms.cpu
            self.deployed_ms_number += 1
            ms.set_deployed_server_from_id(self.id)
            return True
        else:
            return False

    def deploy_mss(self, mss:list):
        """部署微服务列表"""
        ms_all = Microservice(-1, {}, 0)
        ms:Microservice
        for ms in mss:
            ms_all.layers.update(ms.layers)
            ms_all.cpu += ms.cpu
        if self.feasibility_of_deploy(ms_all):
            for ms in mss:
                self.deploy_ms(ms)
        else:
            raise ValueError("Not enough storage or computing power!")

    def undeploy_ms(self, ms:Microservice):
        # 卸载微服务，更新剩余容量
        try:
            self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app].pop(ms.id)
            if len(self.deployed_ms_library[ms.subordinate_device][ms.subordinate_app]) == 0:
                self.deployed_ms_library[ms.subordinate_device].pop(ms.subordinate_app)
                if len(self.deployed_ms_library[ms.subordinate_device]) == 0:
                    self.deployed_ms_library.pop(ms.subordinate_device)
        except:
            raise ValueError("Microservice not deployed!")
        for key in ms.layers.keys():
            if key in self.deployed_layers.keys():
                self.deployed_layers[key] -= 1
                if self.deployed_layers[key] == 0:
                    self.deployed_layers.pop(key)
                    self.left_storage += ms.layers[key]
        # for value in ms.layers.values():
        #     self.left_storage += value
        self.left_computing += ms.cpu
        self.deployed_ms_number -= 1
        ms.set_deployed_server_from_id(None)

    def undeploy_ms_from_id(self, device_id:int, app_id:int, ms_id:int):
        # 通过id卸载微服务
        ms:Microservice
        for ms in self.deployed_ms_library.values():
            if ms.subordinate_app == app_id and ms.id == ms_id and ms.subordinate_device == device_id:
                self.undeploy_ms(ms)
                return
        raise ValueError("No such microservice in server!")

    def show_deployed_ms(self):
        """
        按照设备、应用的分类显示已部署的微服务
        """
        for device_id in self.deployed_ms_library.keys():
            for app_id in self.deployed_ms_library[device_id].keys():
                print("Device:", device_id, "App:", app_id, end=" Microservice:")
                for ms in self.deployed_ms_library[device_id][app_id].values():
                    print(ms.id, end=",")
            print()
        print("------------------------")

    def show_server_state(self):
        """
        实时展示设备状态
        """
        print("Server id:", self.id, "Deployed ms number:", self.deployed_ms_number, "Left storage:", self.left_storage, "Left computing:", self.left_computing)
        self.show_deployed_ms()

class Device:
    def __init__(self, id:int, connected_server_id:int):
        # 设备id
        self.id = id
        # 连接的服务器id
        self.connected_server_id = connected_server_id

        self.request_app_library = {}

    def reset(self):
        self.request_app_library = {}

    def app_id_in_device(self, app_id:int):
        """判断设备中是否有该应用程序"""
        if app_id in self.request_app_library.keys():
            return True
        return False
    
    def get_request_app_from_id(self, app_id:int):
        """获取请求的应用程序"""
        if self.app_id_in_device(app_id):
            return self.request_app_library[app_id]
        raise ValueError("No such application in device!")
    
    def get_request_app_ids(self):
        """获取请求的应用程序的id"""
        return list(self.request_app_library.keys())

    def request_app(self, app:Application):
        """请求应用程序"""
        if app.app_id not in self.request_app_library.keys():
            app.set_subordinate_device(self.id)
            self.request_app_library[app.app_id] = app
        else:
            raise ValueError("Application already requested!")

    def request_apps(self, app_list:list):
        """请求应用程序们"""
        for app in app_list:
            self.request_app(app)

    def cancel_request_app(self, app_id:int):
        """取消请求应用程序"""
        for appid in self.request_app_library.keys():
            if appid == app_id:
                self.request_app_library.pop(appid)
                return
        raise ValueError("No such application in device!")
    
    def move_to_other_server(self, server_id:int):
        """移动到其他服务器"""
        self.connected_server_id = server_id

if __name__ == "__main__":
    # 测试
    from application import create_test_app
    app = create_test_app()
    app2 = create_test_app()
    server = Server(1, 100, 100, 100)
    device = Device(1, 1)

    # app.draw_the_app_with_data()
    device.request_app(app)
    server.deploy_ms(app.microservice_library[1])
    server.deploy_ms(app.microservice_library[2])
    server.deploy_ms(app.microservice_library[3])
    # server.deploy_ms(app2.microservice_library[1])
    # server.undeploy_ms(app.microservice_library[1])
    # server.undeploy_ms(app.microservice_library[2])
    # server.undeploy_ms(app.microservice_library[3])
    # print(server.left_storage)
    # print(server.left_computing)
    # print(server.deployed_ms_number)
    # print(server.deployed_layers)
    # print(server.deployed_ms_library)
    server.show_deployed_ms()


