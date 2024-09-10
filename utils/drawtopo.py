"""
绘制网络拓扑
"""

from environment.migration_environment import Prodution
from algorithm.main_algorithm import Algorithm
from config import get_config
from database import Database
from evaluate import Evaluate
import matplotlib.pyplot as plt
from threading import Thread, Lock
import time, copy, os, pandas as pd


# TIME_SLOT_LENGTH = 20  # 时隙宽度
# END_TIME_SLOT = 200  # 时隙数量


TIME_SLOT_LENGTH = 15  # 时隙宽度
END_TIME_SLOT = 300  # 时隙数量
# PARALLEL_THRESHOLD = 2500  # 平行控制介入阈值
# max = 4065，15实测1845
PARALLEL_THRESHOLD = 2000  # 平行控制介入阈值

PARALLEL_INTERVAL = 8  # 平行控制的时间间隔
parallel_control_action = {}
parallel_control_actionLock = Lock()
parallel_control_flag = False
parallel_control_flagLock = Lock()


def main(set_seed):
    global parallel_control_flag
    global parallel_control_action

    # 数据库创建
    database = Database()

    # 评估模块创建
    evaluate = Evaluate(database=database)

    # 环境模块创建
    production = Prodution(database=database, end_time=END_TIME_SLOT, algorithm_type="None", no_output=True)

    # 算法创建
    Gurobi_algorithm = Algorithm(database=database, algorithm_type="gurobi")

    # 生成环境配置文件
    # config = get_config(
    #     seed=0, device_number=80, server_number=20, application_number=80, microservice_number=200, start_mode="gurobi", end_time=END_TIME_SLOT
    # )
    config = get_config(
        seed=set_seed, device_number=40, server_number=10, application_number=40, microservice_number=80, start_mode="gurobi", end_time=END_TIME_SLOT
    )

    # 从配置文件中创建生产环境
    production.create_environment_from_config(config)

    production.show_hardware()


if __name__ == "__main__":
    for seed in range(25):
        main(seed)
