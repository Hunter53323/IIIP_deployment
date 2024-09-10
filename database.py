# 用于存储所有时刻的数据
import time
import csv
import os
import pandas as pd

class Database:
    """
    数据库，目前是直接用的python字典进行实现的，若有必要可接通真实的数据库
    """
    def __init__(self):
        # 这个data是和时刻相关的变化数据
        self.data = {}

        # 该部分存储静态数据
        self.static_data = {}

    def add(self, t:int, type:str, key, value):
        """
        type: state, action, evaluate,data存储数据格式为:data = {state:{}, action:{}, evaluate:{}}
        """
        if type not in ["state", "action", "evaluate"]:
            raise ValueError("type must be 'state' or 'action' or 'evaluate'")
        if t not in self.data:
            self.data[t] = {}
        if type not in self.data[t]:
            self.data[t][type] = {}
        self.data[t][type][key] = value

    def add_dict(self, t:int, type:str, data:dict):
        """
        type: state, action, evaluate
        """
        if type not in ["state", "action", "evaluate"]:
            raise ValueError("type must be 'state' or 'action' or 'evaluate'")
        if t not in self.data:
            self.data[t] = {}
        if type not in self.data[t]:
            self.data[t][type] = data

    def add_static_data(self, key, value):
        self.static_data[key] = value

    def get_state(self, t:int):
        return self.data[t]["state"]
    
    def get_action(self, t:int):
        return self.data[t]["action"]
    
    def save_to_csv(self, name = "data"):
        self.data_fix()

        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        name_with_timestamp = name + "_" + timestamp + ".csv"
        parent_dir = os.getcwd() + "/output/"
        
        df = pd.DataFrame(columns=['time', 'level_2_key', 'level_3_key', 'value'])
        rows = []
        for level_1_key, level_2_dict in self.data.items():
            for level_2_key, level_3_dict in level_2_dict.items():
                for level_3_key, value in level_3_dict.items():
                    rows.append({'time': level_1_key,
                                    'level_2_key': level_2_key,
                                    'level_3_key': level_3_key,
                                    'value': value})
        df = pd.concat([df, pd.DataFrame(rows)])

        # 按照time和level_2_key+level_3_key创建透视表
        df_pivoted = df.pivot_table(index='time', columns=['level_2_key', 'level_3_key'], values='value',aggfunc='sum')

        # 添加时间戳列到透视表
        df_pivoted.insert(0, 'time', df_pivoted.index)

        # 将透视表写入csv文件
        df_pivoted.to_csv(parent_dir+name_with_timestamp, index=False)

    def reset(self):
        self.data = {}

    def reset_complete(self):
        self.data = {}
        self.static_data = {}

    def data_fix(self):
        """
        数据保存的时候server_microservice_deployment会有问题，返回的是一个dict_keys对象，需要转换成list
        """
        for data in self.data.values():
            for key, value in data.items():
                if key == "state":
                    if "server_microservice_deployment" in value.keys():
                        for value1 in value["server_microservice_deployment"].values():
                            for value2 in value1.values():
                                for key3 in value2.keys():
                                    value2[key3] = list(value2[key3].keys())
        
if __name__ == "__main__":
    DB = Database()
    DB.add(1, "state", "a", 1)
    DB.add(1, "state", "b", 2)
    DB.add(1, "action", "a", 3)
    DB.add(1, "action", "b", 4)
    DB.add(1, "evaluate", "a", 5)
    DB.add(1, "evaluate", "b", 6)
    DB.add(2, "state", "a", 7)
    DB.add(2, "state", "b", 8)
    DB.add(2, "action", "a", 9)

    DB.save_to_csv()
