"""
设置初始参数求解，直到环境运行完毕
"""

from environment.migration_environment import Prodution
from database import Database
from evaluate import Evaluate
from config import CONFIG_ENVIRONMENT, get_config
import time
import matplotlib.pyplot as plt


def main():
    # 创建数据库实例
    database = Database()

    # 创建评估实例，用于评估算法的效果
    evaluate = Evaluate(database=database)

    # 创建实际的生产环境实例，入参的end_time是生产环境的最大时间，到达该事件后则会停止，算法种类为对应的求解算法采用哪种，目前为gurobi(论文中提出的算法)和greedy(贪心算法)和fullgurobi(完全gurobi求解算法)和base(随机算法)
    production = Prodution(database=database, end_time=40, algorithm_type="gurobi")
    # production = Prodution(database=database, end_time=5, algorithm_type="fullgurobi")
    # production = Prodution(database=database, end_time=40, algorithm_type="greedy")

    # 从配置文件中读取配置信息，创建生产环境
    # production.create_environment_from_config(CONFIG_ENVIRONMENT)

    # 根据配置文件生产环境参数创建生产环境，随机生成，start_mode代表初始的部署方案，solve代表初始的时候随机选取一个部署，gurobi代表初始的时候使用fullgurobi求解一个部署方案,greedy代表初始的时候使用贪婪算法求解一个部署方案
    # TODO:可以再加一个使用贪婪算法求解一个部署方案的选项
    # config = get_config(device_number=50, server_number=22,application_number=50,microservice_number=100, start_mode="solve")
    aa = 200
    config = get_config(device_number=aa, server_number=50, application_number=aa, microservice_number=aa * 2, start_mode="greedy", end_time=40)

    # 从配置文件中创建生产环境
    production.create_environment_from_config(config)

    # 生产环境展示，软硬件
    # production.show_hardware()
    # production.show_software()

    # 根据配置文件的start_mode来决定初始的部署方案，并进行预部署启动系统
    production.deploy_start(config["start"])
    # production.show()

    # 设置求解算法的参数，目前只有gurobi算法有参数，epsilon是gurobi算法的内点界高度，output是是否输出求解过程
    # output在fullgurobi算法中也有，决定是否输出求解过程
    production.algorithm.algorithm.output = False
    production.algorithm.algorithm.epsilon = 0.0001

    # 初始环境配置完成，启动系统运行
    while True:
        # 时间前进，若到达最大时间则停止
        if not production.time_next():
            break

        # 进行新时刻的设备移动、服务请求并将数据存到数据库
        production.get_state()

        # 根据当前时刻的状态进行求解，得到动作
        action = production.algorithm_solve()
        # action= {}

        # 根据动作进行移动，更新状态
        production.step(action)

        # 评估当前时刻的系统效果
        print("current time: ", production.current_time)
        # 算法的求解时间
        # print("Solve time:", database.data[production.current_time]["evaluate"]["solve_time"])
        # 微服务迁移成本
        print("Migration cost: ", evaluate.evaluate_migration_cost(production.current_time))
        # 镜像拉取成本
        print("Image pull cost: ", evaluate.evaluate_image_pull_cost(production.current_time))
        # 决策后的通讯开销
        print("Communication cost: ", evaluate.evaluate_communication_cost(production.current_time))
        # 决策前的通讯开销
        print("Communication cost after move: ", evaluate.evaluate_communication_cost_after_move(production.current_time))
        print("----------------------------------")

        # production.show()
        # production.show_hardware()
        # time.sleep(0.2)
        # plt.close()

    # 重置环境
    # production.reset()

    # 将实验数据存到csv文件中
    database.save_to_csv()


if __name__ == "__main__":
    main()

# TODO:评估模块和求解模块需要调整一下三个变量是不是直接相加，最好找一个比较合适的比例
# 思源上最后一个计算系统稳定程度的公式也需要实现一下
