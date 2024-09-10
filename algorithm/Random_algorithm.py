from database import Database
import random
import copy

class RandomAlgorithm():
    """
    随机部署算法，随机找一个可行的进行部署
    """
    def __init__(self, database:Database):
        super().__init__()
        self.database = database

        #静态数据，每个应用程序包含哪些微服务，有哪些服务器，有哪些设备
        self.device_ids = None
        self.server_ids = None
        self.application_ids = None
        self.application_contain_microservice = {}
        #动态数据 设备每次请求的应用程序
        self.device_request = None
        self.solve_result = {}

        self.solve_flag = False

    def get_data(self, time:int):
        if self.device_ids == None:
            self.device_ids = self._get_device_ids()
            self.server_ids = self._get_server_ids()
            self.application_ids = self._get_application_sets()
            for app_id in self.application_ids:
                self.application_contain_microservice[app_id] = self._get_application_contain_microservice_ids(app_id)
            self._set_start_action()

        self.device_request = self._get_device_request(time=time)
        self.solve_flag = True

    def solve(self):
        if self.solve_flag == False:
            raise ValueError("Solve in the wrong order!")
        last_result = copy.deepcopy(self.solve_result)
        if self.device_request != None:
            # 随机部署
            for device_id in self.device_ids:
                self.solve_result[device_id] = {}
                application_ids = self.device_request[device_id]
                for application_id in application_ids:
                    self.solve_result[device_id][application_id] = {}
                    for microservice_id in self.application_contain_microservice[application_id]:
                        self.solve_result[device_id][application_id][microservice_id] = random.choice(self.server_ids)
        else:
            raise ValueError("No data to solve!")
        
        action_result = copy.deepcopy(self.solve_result)
        for device_id in self.device_ids:
            for application_id in self.device_request[device_id]:
                for microservice_id in self.application_contain_microservice[application_id]:
                    if self.solve_result[device_id][application_id][microservice_id] == last_result[device_id][application_id][microservice_id]:
                        # 部署结果无变化
                        action_result[device_id][application_id].pop(microservice_id)
                        if len(action_result[device_id][application_id]) == 0:
                            action_result[device_id].pop(application_id)
                            if len(action_result[device_id]) == 0:
                                action_result.pop(device_id)

        self.solve_flag = False
        action = {"migrate":action_result}
        return action
    
    def _set_start_action(self):
        """
        最开始的时候给求解结果赋值为预部署的结果
        """
        self.solve_result = copy.deepcopy(self.database.data[0]["state"]["microservice_deployment"])

    def _get_server_num(self):
        return self.database.static_data["server_number"]
    
    def _get_device_num(self):
        return self.database.static_data["device_number"]
    
    def _get_device_request(self, time:int):
        return self.database.data[time]["state"]["device_request_app"]
    
    def _get_server_ids(self):
        return list(self.database.static_data["server_library"].keys())
    
    def _get_device_ids(self):
        return list(self.database.static_data["device_library"].keys())
    
    def _get_application_sets(self):
        return self.database.static_data["application_library"]
    
    def _get_application_contain_microservice_ids(self, app_id:int):
        return list(self.database.static_data["application_library"][app_id].microservice_library.keys())