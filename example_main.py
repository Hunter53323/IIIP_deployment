from database import Database
from environment.base_environment import base_Prodution

CONFIG_ENVIRONMENT = {
    # 系统基本参数配置文件
    "device": [
    {"id": 1, "connected_server_id": 1},
    {"id": 2, "connected_server_id": 2},
    {"id": 3, "connected_server_id": 3},
    {"id": 4, "connected_server_id": 4},
    {"id": 5, "connected_server_id": 4},
    ],
    "server": [# 算力单位:GFlopS, 带宽单位:Gbps, 存储单位:GBG
    {"id": 1, "computing": 30, "storage": 32, "bandwidth": 0.1},
    {"id": 2, "computing": 30, "storage": 32, "bandwidth": 0.1},
    {"id": 3, "computing": 30, "storage": 32, "bandwidth": 0.1},
    {"id": 4, "computing": 30, "storage": 32, "bandwidth": 0.1},
    ],
    "topo": [ #边缘服务器的网络拓扑
    {"server_1": 1, "server_2": 2},
    {"server_1": 1, "server_2": 3},
    {"server_1": 1, "server_2": 4},
    {"server_1": 2, "server_2": 3},
    ],
    "application": [ #data单位为KB，sender和receiver为对应的微服务id
    {"id": 1, "name": "app_1", "ms_id_list": [1, 2], "message": [
        {"data": 101, "sender": 1, "receiver": 2}], "source_message_data": 101},
    {"id": 2, "name": "app_2", "ms_id_list": [3, 4, 5], "message": [
        {"data": 102, "sender": 3, "receiver": 4}, 
        {"data": 103, "sender": 4, "receiver": 5}], "source_message_data": 102},
    {"id": 3, "name": "app_3", "ms_id_list": [3, 7, 8], "message": [
        {"data": 104, "sender": 3, "receiver": 7},
        {"data": 105, "sender": 7, "receiver": 8}], "source_message_data": 103},
    {"id": 4, "name": "app_4", "ms_id_list": [6, 7], "message": [
        {"data": 106, "sender": 6, "receiver": 7}], "source_message_data": 104},
    {"id": 5, "name": "app_5", "ms_id_list": [1, 7], "message": [
        {"data": 107, "sender": 1, "receiver": 7}], "source_message_data": 105}
    ],
    "microservice": [ # 层单位GB
    {"id": 1, "layers": {"layer1":0.3}, "cpu": 5, "name": "microservice_1"},
    {"id": 2, "layers": {"layer2":0.4}, "cpu": 3, "name": "microservice_2"},
    {"id": 3, "layers": {"layer3":0.5}, "cpu": 2, "name": "microservice_3"},
    {"id": 4, "layers": {"layer4":0.8}, "cpu": 10, "name": "microservice_4"},
    {"id": 5, "layers": {"layer5":1.2}, "cpu": 1, "name": "microservice_5"},
    {"id": 6, "layers": {"layer6":1.8}, "cpu": 4, "name": "microservice_6"},
    {"id": 7, "layers": {"layer7":0.9}, "cpu": 2, "name": "microservice_7"},
    {"id": 8, "layers": {"layer8":0.2}, "cpu": 5, "name": "microservice_8"},
    ]
}

database = Database()
production = base_Prodution(database=database, end_time=40)
production.create_environment_from_config(CONFIG_ENVIRONMENT)
production.random_deploy()
production.show()