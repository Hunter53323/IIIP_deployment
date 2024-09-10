"""
全局控制算法，用于进行比较
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
PARALLEL_THRESHOLD = 3000  # 平行控制介入阈值

PARALLEL_INTERVAL = 8  # 平行控制的时间间隔
parallel_control_action = None
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

    # 根据配置文件的start_mode来决定初始的部署方案，并进行预部署启动系统
    production.deploy_start(config["start"])

    # 画图的初始配置
    time_list = []
    communication_cost_list = []

    # 是否正在进行平行控制的计算
    parallel_control_flag = False
    # 当前时刻是否有全局更新，两次全局更新不能紧挨着，不然Full_Gurobi算法会出现问题
    refresh_current_time = False

    real_time = time.time()
    while True:
        time_now = time.time()
        time_slot = int((time_now - real_time) / TIME_SLOT_LENGTH)  # 大时隙，表示当前系统处于哪一个大时隙
        system_time_slot = production.current_time  # 系统内部用于记录循环了多少次

        # 如果平行控制里面计算完成，那么进行更新
        if parallel_control_action != None and parallel_control_flag == False:
            # 从全局变量中获取动作
            action = parallel_control_action
            # 根据动作进行移动，更新状态
            production.step(action)
            # 从全局变量中删除动作
            parallel_control_actionLock.acquire()
            parallel_control_action = None
            parallel_control_actionLock.release()
            # 表示当前时刻有全局更新
            refresh_current_time = True

            print("current time: ", production.current_time, ", 平行控制更新")
            print("Communication cost: ", evaluate.evaluate_communication_cost(production.current_time))
            print("----------------------------------")
            # 添加评估数据，用于绘制
            time_list.append(int(time.time() - real_time))
            communication_cost_list.append(evaluate.evaluate_communication_cost(production.current_time))
            continue

        # 平行控制介入阈值
        if system_time_slot != 0 and parallel_control_flag == False and refresh_current_time == False:
            # 两次全局更新不能紧挨着，不然Full_Gurobi算法会出现问题
            # if system_time_slot % PARALLEL_INTERVAL == 0 and system_time_slot != 0 and parallel_control_flag == False:
            # 第一块用于在系统运行一段时间后再进行平行控制，免得出现资源浪费
            # 设置平行控制标志位
            parallel_control_flagLock.acquire()
            parallel_control_flag = True
            parallel_control_flagLock.release()
            # 创建线程
            thread = Thread(target=parallel, args=(production,))
            # 启动线程
            thread.start()

        if time_slot == (system_time_slot + 1):
            refresh_current_time = False
            # 直到第一次跑到下一个时隙才会触发这个
            if not production.time_next():
                break
        else:
            time.sleep(0.2)
            continue

        # 设备移动和服务请求，数据存储到数据库中
        production.get_state()
        production.step({})

        print("current time: ", production.current_time, ", 无优化")
        print("Communication cost: ", evaluate.evaluate_communication_cost(production.current_time))
        print("----------------------------------")

        # 添加画图的数据
        time_list.append(production.current_time * TIME_SLOT_LENGTH)
        communication_cost_list.append(evaluate.evaluate_communication_cost(production.current_time))

    save_to_csv(time_list, global_method=communication_cost_list)
    # 画图，横轴坐标为时间，单位s，纵轴坐标为通信代价，单位KB
    # plt.plot(time_list, communication_cost_list)
    # plt.xlabel("Time(s)")
    # plt.ylabel("Communication cost(KB)")
    # plt.show()


def save_to_csv(time_list, **kargs):
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    name_with_timestamp = "global_data" + "_" + timestamp + ".csv"
    parent_dir = os.getcwd() + "/output/"

    rows = []
    for i in range(len(time_list)):
        rows.append([time_list[i]] + [kargs[key][i] for key in kargs.keys()])

    df = pd.DataFrame(data=rows, columns=["time"] + list(kargs.keys()))
    # 将透视表写入csv文件
    df.to_csv(parent_dir + name_with_timestamp, index=False)


def parallel(production: Prodution):
    global parallel_control_flag
    global parallel_control_action
    # 计时
    time_count_1 = time.time()
    print("时隙", production.current_time, ",平行控制系统开始计算")
    # 平行控制系统中最终输出的动作
    final_action = {}

    parallel_production: Prodution = copy.deepcopy(production)
    parallel_database: Database = parallel_production.db

    Full_Gurobi_Algorithm: Algorithm = Algorithm(database=parallel_database, algorithm_type="fullgurobi")

    action = parallel_production.algorithm_solve(Full_Gurobi_Algorithm)

    parallel_production.step(action)

    final_action = action

    # 将最终的动作和时间存储到全局变量
    parallel_control_actionLock.acquire()
    parallel_control_action = final_action
    parallel_control_actionLock.release()
    # 设置平行控制标志位
    parallel_control_flagLock.acquire()
    parallel_control_flag = False
    parallel_control_flagLock.release()

    time_count_2 = time.time()

    print("平行控制系统计算时间：", round(time_count_2 - time_count_1, 2), "s")


if __name__ == "__main__":
    for seed in range(5, 25):
        main(seed)
