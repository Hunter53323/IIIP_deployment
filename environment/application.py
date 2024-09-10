# 应用程序和微服务基类
import networkx as nx
import matplotlib.pyplot as plt 

class Microservice:
    """
    微服务类
    """
    def __init__(self, id:int, layers:dict, cpu:float, name:str = None):
        self.layers = layers #传入的layer是个字典，包括名称和大小
        self.cpu = cpu
        self.id = id
        self.name = name
        self.next_ms = []
        self.previous_ms = []
        self.subordinate_app = None
        self.subordinate_device = None
        self._deployed_server = None

    def set_deployed_server_from_id(self, server_id = None):
        self._deployed_server = server_id

    def get_deployed_server_id(self):
        return self._deployed_server
    
    def reset(self):
        pass

class Message:
    """
    消息类，用于传递数据
    """
    def __init__(self, data:float, sender:int, receiver:int, frequency:int = 1):
        self.data = data * frequency
        self.sender = sender
        self.receiver = receiver

class Application:
    """
    应用程序类，包含多个微服务
    """
    def __init__(self, name:str, app_id:int):
        self.name = name
        self.message = []
        self.length = 0
        self.microservice_library = {}
        self.app_id = app_id
        self.subordinate_device = None
        self.source_message = None

    def reset(self):
        pass

    def find_head(self):
        """
        找到应用程序的头节点
        """
        ms:Microservice
        for ms in self.microservice_library.values():
            if len(ms.previous_ms) == 0:
                return ms.id
        raise ValueError("No head node in application!")

    def check_deployment(self):
        """
        检查应用程序的部署情况
        """
        ms:Microservice
        for ms in self.microservice_library.values():
            if ms.get_deployed_server_id() is None:
                return False
        return True

    def get_microservice_from_id(self, id:int):
        ms:Microservice
        for ms in self.microservice_library.values():
            if ms.id == id:
                return ms
        raise ValueError("No such microservice in application!")

    def set_subordinate_device(self, device_id:int):
        """
        设置应用程序和微服务所属设备
        """
        self.subordinate_device = device_id
        microservice:Microservice
        for microservice in self.microservice_library.values():
            microservice.subordinate_device = device_id

    def add_microservice(self, ms:Microservice):
        """
        对应用程序添加微服务
        """
        if ms.id in self.microservice_library.keys():
            raise ValueError("Microservice id already in application!")
        self.microservice_library[ms.id] = ms
        self.length += 1
        ms.subordinate_app = self.app_id

    def add_microservices(self, ms_list:list):
        """
        对应用程序添加微服务
        """
        for ms in ms_list:
            self.add_microservice(ms)

    def create_ms_from_config(self, ms_id:int, config:dict):
        """
        通过配置文件创建微服务
        """
        pass

    def get_ms_from_id(self, id:int):
        """
        通过id查找微服务
        """
        if id not in self.microservice_library.keys():
            raise ValueError("No such microservice in application!")
        ms:Microservice = self.microservice_library[id]
        return ms
    
    def ms_id_in_app(self, id:int):
        """
        判断微服务是否在应用程序中
        """
        if id in self.microservice_library.keys():
            return True
        else:
            return False
    
    def get_data_from_message(self, sender:int, receiver:int):
        """
        通过消息获取数据
        """
        id_keys = [0] + list(self.microservice_library.keys())
        if sender not in id_keys or receiver not in id_keys:
            raise ValueError("microservice id not in application!")
        
        if sender == 0 and receiver == self.find_head():
            return self.source_message["data"]
        
        message:Message
        for message in self.message:
            if message.sender == sender and message.receiver == receiver:
                return message.data
        return 0

    def add_message(self, message:Message):
        """
        添加消息
        """
        if message.sender in self.microservice_library.keys() and message.receiver in self.microservice_library.keys():
            self.message.append(message)
            self.microservice_library[message.sender].next_ms.append(message.receiver)
            self.microservice_library[message.receiver].previous_ms.append(message.sender)
        else:
            raise ValueError("Message sender or receiver not in application!")
        
    def add_source_message(self, data:float):
        """
        添加源消息
        """
        head_id = self.find_head()
        self.source_message = {"data":data, "receiver":head_id}
        
    def add_messages(self, message_list:list):
        """
        添加消息
        """
        for message in message_list:
            self.add_message(message)

    def draw_the_app(self):
        """
        绘制应用程序
        """
        G = nx.DiGraph()
        ms:Microservice
        for ms in self.microservice_library.values():
            G.add_node(ms.id, cpu = ms.cpu)
        message:Message
        for message in self.message:
            G.add_edge(message.sender, message.receiver, data = message.data)
        nx.draw(G, with_labels = True)
        plt.show()

    def draw_the_app_with_data(self):
        """
        绘制带有通讯数据的应用程序
        """
        G = nx.DiGraph()
        ms:Microservice
        for ms in self.microservice_library.values():
            G.add_node(ms.id, cpu=ms.cpu)
        message:Message
        for message in self.message:
            G.add_edge(message.sender, message.receiver, data=message.data)
        
        pos = nx.spring_layout(G) 
        # 设定节点的layout算法；spring_layout产生一个力学模型的布局。 
        
        edge_labels = nx.get_edge_attributes(G, 'data')     # 获取边属性data到labels
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)    # 绘制带权重的图（可以直接放在nx.draw()后）
        
        nx.draw(G, pos, with_labels=True)
        plt.show()
        
def create_test_app():
    test_ms_1 = Microservice(id = 1, layers = {"layer1": 1}, cpu = 1)
    test_ms_2 = Microservice(id = 2, layers = {"layer2": 1}, cpu = 0.4)
    test_ms_3 = Microservice(id = 3, layers = {"layer3": 1}, cpu = 0.2)
    test_ms_4 = Microservice(id = 4, layers = {"layer4": 1}, cpu = 0.1)

    test_message_1 = Message(data = 100, sender = 1, receiver = 2)
    test_message_2 = Message(data = 200, sender = 2, receiver = 3)
    test_message_3 = Message(data = 300, sender = 2, receiver = 4)

    test_app = Application(name = "test_app", app_id = 1)

    test_app.add_microservices([test_ms_1, test_ms_2, test_ms_3, test_ms_4])
    test_app.add_messages([test_message_1, test_message_2, test_message_3])

    return test_app

if __name__ == "__main__":
    test_app = create_test_app()

    test_app.draw_the_app_with_data()
