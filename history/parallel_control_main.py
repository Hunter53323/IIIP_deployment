"""
基础并行控制算法，其中修正部分考虑的比较简单，是直接叠加的快速求解算法
"""

from environment.migration_environment import Prodution
from algorithm.main_algorithm import Algorithm
from config import get_config
from database import Database
from evaluate import Evaluate
import matplotlib.pyplot as plt
from threading import Thread, Lock
import time, copy


TIME_SLOT_LENGTH = 1  # 时隙宽度
END_TIME_SLOT = 200  # 时隙数量
parallel_control_action = {}
parallel_control_actionLock = Lock()
parallel_control_flag = False
parallel_control_flagLock = Lock()


def main():
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
        seed=0, device_number=20, server_number=5, application_number=20, microservice_number=40, start_mode="gurobi", end_time=END_TIME_SLOT
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
    start_time_deployment = None
    end_time_deployment = None

    real_time = time.time()
    while True:
        time_now = time.time()
        time_slot = int((time_now - real_time) / TIME_SLOT_LENGTH)  # 大时隙，表示当前系统处于哪一个大时隙
        system_time_slot = production.current_time  # 系统内部用于记录循环了多少次

        # 如果平行控制里面计算完成，那么进行更新
        if system_time_slot in parallel_control_action.keys() and parallel_control_flag == False:
            # 获取结束时的系统微服务部署状态
            end_time_deployment = production.get_deployment(production.current_time)
            # 计算需要回退的微服务
            move_back_action = move_back(start_time_deployment, end_time_deployment)
            # 从全局变量中获取动作
            decision_action = parallel_control_action[system_time_slot]
            # 将回退的微服务和平行控制的微服务进行合并
            action = move_refresh(move_back_action, decision_action)
            # 根据动作进行移动，更新状态
            production.step(action)
            # 从全局变量中删除动作
            parallel_control_actionLock.acquire()
            del parallel_control_action[system_time_slot]
            parallel_control_actionLock.release()

            print("current time: ", production.current_time, ", 平行控制更新")
            print("Communication cost: ", evaluate.evaluate_communication_cost(production.current_time))
            print("----------------------------------")
            time_list.append(int(time.time() - real_time))
            communication_cost_list.append(evaluate.evaluate_communication_cost(production.current_time))

        if system_time_slot % 30 == 0 and system_time_slot != 0 and parallel_control_flag == False:
            # 第一块用于在系统运行一段时间后再进行平行控制，免得出现资源浪费
            # 设置平行控制标志位
            parallel_control_flagLock.acquire()
            parallel_control_flag = True
            parallel_control_flagLock.release()

            start_time_deployment = production.get_deployment(production.current_time)
            # 创建线程
            thread = Thread(target=parallel, args=(production,))
            # 启动线程
            thread.start()

        if time_slot == (system_time_slot + 1) and system_time_slot not in parallel_control_action.keys():
            # 直到第一次跑到下一个时隙才会触发这个
            if not production.time_next():
                break
        else:
            time.sleep(0.2)
            continue

        # 设备移动和服务请求，数据存储到数据库中
        production.get_state()

        # 运行给定的算法，得到部署方案
        action = production.algorithm_solve(Gurobi_algorithm)

        # 根据动作进行移动，更新状态
        production.step(action)

        print("current time: ", production.current_time, ", 启动优化")
        print("Communication cost: ", evaluate.evaluate_communication_cost(production.current_time))
        print("----------------------------------")

        # 添加画图的数据
        time_list.append(production.current_time * TIME_SLOT_LENGTH)
        communication_cost_list.append(evaluate.evaluate_communication_cost(production.current_time))

    # 画图，横轴坐标为时间，单位s，纵轴坐标为通信代价，单位KB
    plt.plot(time_list, communication_cost_list)
    plt.xlabel("Time(s)")
    plt.ylabel("Communication cost(KB)")
    plt.show()


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

    while production.current_time != parallel_production.current_time:
        if parallel_production.current_time > production.current_time:
            raise Exception("模拟时刻快于实际时刻")
        if not parallel_production.time_next():
            return

        # 从真实环境中获取当前时刻的变化信息
        movement = production.get_movement(parallel_production.current_time)

        # 根据当前的变化信息进行虚拟环境的更新
        parallel_production.get_state_with_input(movement, {})

        # 运行给定的算法，得到部署方案
        Gurobi_ALgorithm: Algorithm = Algorithm(database=parallel_database, algorithm_type="gurobi")

        action = parallel_production.algorithm_solve(Gurobi_ALgorithm)

        parallel_production.step(action)

        # 对最终的final action进行更新
        final_action = add_action(final_action["migrate"], action["migrate"])

    # 将最终的动作和时间存储到全局变量
    parallel_control_actionLock.acquire()
    parallel_control_action[production.current_time] = final_action
    parallel_control_actionLock.release()
    # 设置平行控制标志位
    parallel_control_flagLock.acquire()
    parallel_control_flag = False
    parallel_control_flagLock.release()

    time_count_2 = time.time()

    print("平行控制系统计算时间：", round(time_count_2 - time_count_1, 2), "s")


def add_action(last_action: dict, new_action: dict):
    """
    将两个动作进行合并，返回新的动作
    """
    app_set: dict
    ms_set: dict
    for device_id, app_set in new_action.items():
        for app_id, ms_set in app_set.items():
            for ms_id, server_id in ms_set.items():
                if device_id not in last_action.keys():
                    last_action[device_id] = {}
                if app_id not in last_action[device_id].keys():
                    last_action[device_id][app_id] = {}
                last_action[device_id][app_id][ms_id] = server_id
    return {"migrate": last_action}


def move_back(start_deployment: dict, end_deployment: dict):
    """
    将部署方案进行回退
    """
    move_back_action: dict = {}
    app_set: dict
    ms_set: dict
    for device_id, app_set in start_deployment.items():
        for app_id, ms_set in app_set.items():
            for ms_id, server_id in ms_set.items():
                if start_deployment[device_id][app_id][ms_id] != end_deployment[device_id][app_id][ms_id]:
                    if device_id not in move_back_action.keys():
                        move_back_action[device_id] = {}
                    if app_id not in move_back_action[device_id].keys():
                        move_back_action[device_id][app_id] = {}
                    move_back_action[device_id][app_id][ms_id] = server_id
    return {"migrate": move_back_action}


def move_refresh(move_back_action, decision_action):
    """
    将回退和平行控制的动作进行合并
    """
    result = {}
    back_action: dict = move_back_action["migrate"]
    decision_action: dict = decision_action["migrate"]

    result = back_action
    for device_id, app_set in decision_action.items():
        for app_id, ms_set in app_set.items():
            for ms_id, server_id in ms_set.items():
                if device_id not in result.keys():
                    result[device_id] = {}
                if app_id not in result[device_id].keys():
                    result[device_id][app_id] = {}
                result[device_id][app_id][ms_id] = server_id
    return {"migrate": result}


if __name__ == "__main__":
    main()
