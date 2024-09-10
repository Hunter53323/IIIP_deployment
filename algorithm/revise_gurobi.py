# Gurobi算法求解，输入参数，输出结果
from database import Database
from environment.application import Microservice, Application
import random
import copy
import numpy as np
import networkx as nx
import gurobipy as gp
from gurobipy import GRB


class ReviseGurobiAlgorithm:
    """
    Gurobi求解算法，目前没有继承，如果需要额外的算法的话那么可以把数据读取抽出来一个基类进行继承
    """

    def __init__(self, database: Database, epsilon: float = 0.001):
        self.database = database

        self.epsilon = epsilon

        # 动态数据 设备每次请求的应用程序
        # self.device_request = None
        self.solve_result = {}
        self.microservice_deployment_last = None
        self.server_deploy_microservice = None
        self.device_connected_server_last = None

        self.output = False  # 算法求解输出
        self.solve_flag = False
        self.pass_flag = False
        self.model = None
        self.x = None
        self.m_list = None
        self.k_list = None

    # ------------------------基础数据模块，通过对数据库的访问返回基础数据------------------------
    @property
    def server_num(self):
        return self.database.static_data["server_number"]

    @property
    def device_num(self):
        return self.database.static_data["device_number"]

    @property
    def server_ids(self):
        return sorted(self.database.static_data["server_library"].keys())

    @property
    def device_ids(self):
        return sorted(self.database.static_data["device_library"].keys())

    @property
    def application_library(self):
        return self.database.static_data["application_library"]

    @property
    def migration_cost_config(self):
        return self.database.static_data["migration_cost"]

    @property
    def microservice_library(self):
        return self.database.static_data["microservice_library"]

    @property
    def server_library(self):
        return self.database.static_data["server_library"]

    @property
    def matrix_D(self):
        """
        该函数的作用是计算矩阵D，函数系列4
        """
        D = np.zeros((self.server_num, self.server_num))
        for i in range(self.server_num):
            for j in range(self.server_num):
                D[i][j] = self.get_server_hops(i + 1, j + 1)
        return D

    # ------------------------时变数据获取模块，通过对数据库的访问返回时变数据------------------------

    def device_request(self, device_id, time: int):
        """
        返回设备请求的应用程序
        """
        return self.database.data[time]["state"]["device_request_app"][device_id]

    def get_server_deploy_microservice(self, time: int):
        """
        返回给定时刻服务器部署的微服务列表
        """
        self.server_deploy_microservice = self.database.data[time]["state"]["server_microservice_deployment"]

    def application_contain_microservice_ids(self, app_id: int):
        """
        获得应用程序包含的微服务id
        """

        key_list = list(self.database.static_data["application_library"][app_id].microservice_library.keys())
        return [0] + key_list

    def application_contain_microservice_number(self, app_id: int):
        """
        获得应用程序包含的微服务数量,不包括初始微服务
        """
        return len(self.database.static_data["application_library"][app_id].microservice_library)

    def get_deployment_from_database(self, time: int):
        """
        该函数的作用是从数据库获得给定时刻的部署方案，用作初始化
        """
        self.microservice_deployment_last = copy.deepcopy(self.database.data[time]["state"]["microservice_deployment"])
        self.device_connected_server_last = copy.deepcopy(self.database.data[time]["state"]["device_connect_to_server"])

    def get_device_connected_server(self, time: int, device_id: int):
        """
        该函数的作用是获得给定时刻的设备连接的服务器
        """
        return self.database.data[time]["state"]["device_connect_to_server"][device_id]

    def get_microservice_deployment_return(self, time: int):
        """
        该函数的作用是获得给定时刻的微服务部署方案,只返回部署结果
        """
        return copy.deepcopy(self.database.data[time]["state"]["microservice_deployment"])

    def get_microservice_size(self, microservice_id: int):
        """
        该函数的作用是获得给定微服务的大小
        """
        microservice: Microservice = self.microservice_library[microservice_id]
        return sum(microservice.layers.values())

    def get_microservice_cpu(self, microservice_id: int):
        """
        该函数的作用是获得给定微服务的计算能力
        """
        microservice: Microservice = self.microservice_library[microservice_id]
        return microservice.cpu

    def get_server_bandwidth(self, server_id: int):
        """
        该函数的作用是获得给定服务器的带宽
        """
        return self.server_library[server_id].bandwidth

    def get_server_storage(self, server_id: int):
        """
        该函数的作用是获得给定服务器的存储空间
        """
        return self.server_library[server_id].storage

    def get_server_computing(self, server_id: int):
        """
        该函数的作用是获得给定服务器的计算能力
        """
        return self.server_library[server_id].computing

    # ------------------------比较复杂数据的获取及处理------------------------

    def get_changed_devices_and_applications(self, time: int):
        """
        该函数的作用是根据当前时刻和上一时刻的位置信息，获得发生变化的设备和应用程序
        当前不考虑应用请求发生变化的情况，只考虑设备发生移动的情况
        """
        m_k_dict = {}
        if "movement" not in self.database.data[time]["state"].keys():
            return m_k_dict
        move_device = self.database.data[time]["state"]["movement"]
        for move_dict in move_device:
            device_id = move_dict["device_id"]
            device_request_applications = self.database.data[time]["state"]["device_request_app"][device_id]
            if device_id not in m_k_dict.keys():
                m_k_dict[device_id] = device_request_applications
        return m_k_dict

    def get_deployemnt(self, device_id, application_id, microservice_id):
        """
        该函数的作用是根据当前时刻获得当前时刻的部署方案,并转化为one hot编码
        """
        if self.microservice_deployment_last == None:
            raise ValueError("Get deployment in the wrong order!")
        if microservice_id == 0:
            deployed_server = self.device_connected_server_last[device_id]
        else:
            deployed_server = self.microservice_deployment_last[device_id][application_id][microservice_id]
        one_hot = np.zeros(self.server_num)
        one_hot[deployed_server - 1] = 1
        return one_hot

    def check_server_deploy_microservice(self, server_id, microservice_id):
        """
        该函数的作用是获得给定服务器id上是否部署有指定的微服务
        """
        deploy_dict: dict = self.server_deploy_microservice[server_id]
        device_dict: dict
        application_dict: dict
        for device_dict in deploy_dict.values():
            for application_dict in device_dict.values():
                for ms_id in application_dict.keys():
                    if ms_id == microservice_id:
                        return True

    def get_server_hops(self, server_id_1: int, server_id_2: int):
        """
        该函数的作用是获得给定两个服务器之间的跳数
        """
        topo = self.database.static_data["topo"]
        return nx.shortest_path_length(topo, source=server_id_1, target=server_id_2)

    def get_communication(self, application_id: int, microservice_id_1: int, microservice_id_2: int):
        """
        该函数的作用是获取给定应用中两个微服务之间的通信量,函数系列4
        """
        application: Application = self.application_library[application_id]
        return application.get_data_from_message(microservice_id_1, microservice_id_2)

    # ------------------------辅助函数------------------------

    def find_microservice_base(self, device_id, application_id, mk_list):
        """
        找到对应的应用程序在mk_list中所处的位置
        """
        microservice_count = 0
        for idx in range(len(mk_list)):
            m, k = mk_list[idx]
            if m == device_id and k == application_id:
                return microservice_count
            microservice_count += self.application_contain_microservice_number(k) + 1
        return microservice_count

    # ------------------------和算法有关的功能函数，数值计算部分------------------------

    def _get_migration_cost_details(self, microservice_id: int, server_id: int):
        """
        获取给定微服务迁移到服务器的迁移代价，函数系列1（理论上应该是从服务器1迁移到服务器2的代价，目前没有考虑）
        """
        for one in self.migration_cost_config:
            if one["microservice_id"] == microservice_id and one["server_id"] == server_id:
                return one["cost"]
        if microservice_id == 0:
            return 0

    def _calculate_C_m_k_i_1_n(self, device_id: int, application_id: int, microservice_id: int, server_id: int):
        """
        该函数的作用是计算迁移代价，函数系列1
        """
        x_m_k_i_t_pre = self.get_deployemnt(device_id, application_id, microservice_id)
        I_i_n = np.zeros(self.server_num)
        for ids in self.server_ids:
            I_i_n[ids - 1] = self._get_migration_cost_details(microservice_id, server_id)
        return np.dot(x_m_k_i_t_pre, I_i_n)

    def calculate_C_m_k_i_1(self, device_id: int, application_id: int, microservice_id: int):
        """
        该函数的作用是计算迁移代价，函数系列1
        """
        C_m_k_i_1 = np.zeros(self.server_num)
        for server_id in self.server_ids:
            C_m_k_i_1[server_id - 1] = self._calculate_C_m_k_i_1_n(device_id, application_id, microservice_id, server_id)
        return C_m_k_i_1

    def _calculate_C_m_k_i_2_n(self, microservice_id: int, server_id: int):
        """
        该函数的作用是计算给定的微服务部署到服务器上的镜像拉取时间，函数系列2
        """
        if microservice_id == 0:
            return 0
        if self.check_server_deploy_microservice(server_id, microservice_id):
            return 0
        else:
            return self.get_microservice_size(microservice_id) / self.get_server_bandwidth(server_id)

    def calculate_C_m_k_i_2(self, device_id: int, application_id: int, microservice_id: int):
        """
        该函数的作用是计算镜像拉取时间组成的向量，函数系列2
        """
        C_m_k_i_2 = np.zeros(self.server_num)
        for server_id in self.server_ids:
            C_m_k_i_2[server_id - 1] = self._calculate_C_m_k_i_2_n(microservice_id, server_id)
        return C_m_k_i_2

    def big_epsilon(self, dimension, epsilon: float = 0.01):
        """
        该函数的作用是计算大的epsilon,函数系列3
        """
        if type(dimension) == int:
            return np.ones(dimension) / epsilon
        elif type(dimension) == tuple:
            return np.eye(dimension[0], dimension[1]) / epsilon
        else:
            raise ValueError("The dimension is not a int or tuple!")

    def calculate_Matrix_M_m_k_i(self, device_id: int, application_id: int, microservice_id: int, epsilon: float = 0.01):
        """
        该函数的作用是计算矩阵M_m_k_i，函数系列3
        """
        C_1 = self.calculate_C_m_k_i_1(device_id, application_id, microservice_id) * 0.5
        C_2 = self.calculate_C_m_k_i_2(device_id, application_id, microservice_id) * 0.5
        EP = self.big_epsilon(self.server_num, epsilon)
        return C_1 + C_2 + EP

    def calculate_Matrix_M_m_k(self, device_id: int, application_id: int, epsilon: float = 0.01):
        """
        该函数的作用是计算矩阵M_m_k，函数系列3
        """
        M_m_k = np.array([])
        for microservice_id in self.application_contain_microservice_ids(application_id):
            M_m_k = np.append(M_m_k, self.calculate_Matrix_M_m_k_i(device_id, application_id, microservice_id, epsilon))
        return M_m_k

    def calculate_W_k_ii(self, application_id: int, microservice_id_1: int, microservice_id_2: int, epsilon: float = 0.01):
        """
        该函数的作用是计算矩阵W_k_ii，函数系列4
        """
        return self.get_communication(application_id, microservice_id_1, microservice_id_2) * self.matrix_D

    def calculate_W_k(self, application_id: int, epsilon: float = 0.01):
        """
        该函数的作用是计算矩阵W_k，函数系列4
        """
        W_k = np.empty((0, self.server_num * (self.application_contain_microservice_number(application_id) + 1)))
        for microservice_id_1 in self.application_contain_microservice_ids(application_id):
            W_k_middle = np.empty((self.server_num, 0))
            for microservice_id_2 in self.application_contain_microservice_ids(application_id):
                W_k_middle = np.hstack((W_k_middle, self.calculate_W_k_ii(application_id, microservice_id_1, microservice_id_2, epsilon)))
            W_k = np.vstack((W_k, W_k_middle))
        W_k = 0.05 * W_k - 1 / epsilon * np.eye(W_k.shape[0], W_k.shape[1])
        return W_k

    # ------------------------约束部分------------------------

    def constraint_1_throw(self, gurobi_model, variable_x, m, k, time, epsilon: float = 0.01):
        """
        该函数的作用是计算约束1，服务器资源的约束,这个约束的除法表示有问题，已经弃用
        """
        # TODO:目前也只考虑一个设备只请求一个应用程序的情况
        deployment_result_last = self.get_microservice_deployment_return(time - 1)
        for n in self.server_ids:
            total_total_sum = 0
            test = 0
            for microservice_id in self.microservice_library.keys():
                total_sum_numerator = 0
                total_sum_denominator = 0
                sum_except_variables = 0
                for device_id in self.device_ids:
                    for application_id in self.device_request(device_id, time):
                        if device_id == m and application_id == k:
                            continue
                        if self.application_contain_microservice_ids(application_id).count(microservice_id) == 0:
                            continue
                        if deployment_result_last[device_id][application_id][microservice_id] == n:
                            sum_except_variables += 1
                            test += 1 * self.get_microservice_size(microservice_id)
                microservice_id_list = self.application_contain_microservice_ids(k)
                if microservice_id_list.count(microservice_id) == 0:
                    total_sum_numerator += sum_except_variables * self.get_microservice_size(microservice_id)
                    total_sum_denominator += sum_except_variables + epsilon
                else:
                    microservice_id_index = microservice_id_list.index(microservice_id)
                    # 到这里开始加上变量了
                    sum_except_variables += variable_x[microservice_id_index * self.server_num + n - 1]
                    total_sum_numerator += sum_except_variables * self.get_microservice_size(microservice_id)
                    total_sum_denominator += sum_except_variables + epsilon
                gurobi_divide = gp.LinExpr()
                gurobi_divide += total_sum_numerator
                gurobi_divide -= total_sum_denominator
                total_total_sum += gurobi_divide
            gurobi_model.addConstr(total_total_sum <= self.get_server_storage(n), name="constraint_1")
            # print("constraint_1", n, "finished")

    # def constraint_1(self, gurobi_model, variable_x, m, k, time, epsilon:float = 0.01):
    #     """
    #     该函数的作用是计算约束1，服务器资源的约束
    #     """
    #     # TODO:目前也只考虑一个设备只请求一个应用程序的情况
    #     deployment_result_last = self.get_microservice_deployment_return(time-1)
    #     for n in self.server_ids:
    #         total_total_sum = 0
    #         deployed_size = 0
    #         variables_sum = 0
    #         for microservice_id in self.microservice_library.keys():
    #             sum_except_variables = 0
    #             for device_id in self.device_ids:
    #                 for application_id in self.device_request(device_id, time):
    #                     if device_id == m and application_id == k:
    #                         continue
    #                     if self.application_contain_microservice_ids(application_id).count(microservice_id) == 0:
    #                         # 当前应用程序里面有没有这个微服务
    #                         continue
    #                     if deployment_result_last[device_id][application_id][microservice_id] == n:
    #                         # 有微服务部署，那么这个值就是1
    #                         sum_except_variables = 1
    #             # 已经部署的微服务的大小至少是这些
    #             deployed_size += sum_except_variables*self.get_microservice_size(microservice_id)
    #             microservice_id_list = self.application_contain_microservice_ids(k)
    #             if microservice_id_list.count(microservice_id) != 0:
    #                 # 若该微服务在当前应用程序中，那么就要考虑变量
    #                 microservice_id_index = microservice_id_list.index(microservice_id)
    #                 expected_variables = variable_x[microservice_id_index * self.server_num + n - 1]
    #                 # 会有重复，但是这是线性化的唯一办法了
    #                 variables_sum += expected_variables*self.get_microservice_size(microservice_id)
    #         total_total_sum += variables_sum + deployed_size
    #         gurobi_model.addConstr(total_total_sum <= self.get_server_storage(n), name="constraint_1")
    #         # print("constraint_1", n, "finished")

    # def constraint_2(self, gurobi_model, variable_x, m, k, time, epsilon:float = 0.01):
    #     """
    #     计算资源的约束，也是单应用程序请求的情况
    #     """
    #     deployment_result_last = self.get_microservice_deployment_return(time-1)
    #     for n in self.server_ids:
    #         total_total_sum = 0
    #         for device_id in self.device_ids:
    #             for application_id in self.device_request(device_id, time):
    #                 if device_id == m and application_id == k:
    #                     for microservice_id in self.application_contain_microservice_ids(application_id):
    #                         if microservice_id == 0:
    #                             # 0号微服务没有算力占用
    #                             continue
    #                         if microservice_id in self.application_contain_microservice_ids(k):
    #                             total_total_sum += self.find_variable_deploy(variable_x, m, k, microservice_id, n)* self.get_microservice_cpu(microservice_id)
    #                 else:
    #                     for microservice_id in self.application_contain_microservice_ids(application_id):
    #                         if microservice_id == 0:
    #                             # 0号微服务没有算力占用
    #                             continue
    #                         if deployment_result_last[device_id][application_id][microservice_id] == n:
    #                             total_total_sum += 1 * self.get_microservice_cpu(microservice_id)
    #         gurobi_model.addConstr(total_total_sum <= self.get_server_computing(n), name="constraint_2")
    #         # print("constraint_2", n, "finished")

    # def constraint_3(self, gurobi_model, variable_x, m, k, time, epsilon:float = 0.01):
    #     """
    #     部署唯一性约束
    #     """
    #     for microservice_id in self.application_contain_microservice_ids(k):
    #         sum = 0
    #         for n in self.server_ids:
    #             sum += self.find_variable_deploy(variable_x, m, k, microservice_id, n)
    #         gurobi_model.addConstr(sum == 1, name="constraint_3")

    # def constraint_4(self, gurobi_model, variable_x, m, k, time, epsilon:float = 0.01):
    #     """
    #     初始微服务的约束，这个限定了某些变量的取值
    #     """
    #     server_id = self.find_initial_microservice_deploy(m, k, time)
    #     matrix = np.zeros(self.server_num)
    #     matrix[server_id - 1] = 1
    #     gurobi_model.addConstrs((variable_x[i] == matrix[i] for i in range(self.server_num)), name="constraint_4")

    def constraint_1(self, gurobi_model, variable_x, m_list, k_list, time, epsilon: float = 0.01):
        """
        该函数的作用是计算约束1，服务器资源的约束
        """
        if len(m_list) != len(k_list):
            raise ValueError("The number of devices is not equal to the number of applications!")

        for i in range(len(m_list)):
            m = m_list[i]
            k = k_list[i]

        deployment_result_last = self.get_microservice_deployment_return(time - 1)
        for n in self.server_ids:
            total_total_sum = 0
            deployed_size = 0
            variables_sum = 0
            for microservice_id in self.microservice_library.keys():
                sum_except_variables = 0
                for device_id in self.device_ids:
                    for application_id in self.device_request(device_id, time):
                        mk_list = list(zip(m_list, k_list))
                        if (device_id, application_id) in mk_list:
                            continue
                        # if device_id == m and application_id == k:
                        #     continue
                        if self.application_contain_microservice_ids(application_id).count(microservice_id) == 0:
                            # 当前应用程序里面有没有这个微服务
                            continue
                        if deployment_result_last[device_id][application_id][microservice_id] == n:
                            # 有微服务部署，那么这个值就是1
                            sum_except_variables = 1
                # 已经部署的微服务的大小至少是这些
                deployed_size += sum_except_variables * self.get_microservice_size(microservice_id)

                # microservice_id_list = self.application_contain_microservice_ids(k)

                microservice_id_list = []
                for k in k_list:
                    microservice_id_list += self.application_contain_microservice_ids(k)
                    # 保证不重复
                # microservice_id_list = list(set(microservice_id_list))

                if microservice_id_list.count(microservice_id) != 0:
                    # 若该微服务在当前应用程序中，那么就要考虑变量
                    # microservice_id_index = microservice_id_list.index(microservice_id)
                    microservice_id_indexs = find_all_indices(microservice_id_list, microservice_id)
                    for microservice_id_index in microservice_id_indexs:
                        expected_variables = variable_x[microservice_id_index * self.server_num + n - 1]
                        # 会有重复，但是这是线性化的唯一办法了
                        variables_sum += expected_variables * self.get_microservice_size(microservice_id)
            total_total_sum += variables_sum + deployed_size
            gurobi_model.addConstr(total_total_sum <= self.get_server_storage(n), name="constraint_1")
            # print("constraint_1", n, "finished")

    def constraint_2(self, gurobi_model, variable_x, m_list, k_list, time, epsilon: float = 0.01):
        """
        计算资源的约束，也是单应用程序请求的情况
        """
        deployment_result_last = self.get_microservice_deployment_return(time - 1)
        for n in self.server_ids:
            total_total_sum = 0
            for device_id in self.device_ids:
                for application_id in self.device_request(device_id, time):
                    mk_list = list(zip(m_list, k_list))
                    if (device_id, application_id) in mk_list:
                        for microservice_id in self.application_contain_microservice_ids(application_id):
                            if microservice_id == 0:
                                # 0号微服务没有算力占用
                                continue
                            # 有修改的部分
                            microservice_base = self.find_microservice_base(device_id, application_id, mk_list) * self.server_num
                            total_total_sum += self.find_variable_deploy(
                                variable_x, device_id, application_id, microservice_id, n, microservice_base
                            ) * self.get_microservice_cpu(microservice_id)
                    else:
                        for microservice_id in self.application_contain_microservice_ids(application_id):
                            if microservice_id == 0:
                                # 0号微服务没有算力占用
                                continue
                            if deployment_result_last[device_id][application_id][microservice_id] == n:
                                total_total_sum += 1 * self.get_microservice_cpu(microservice_id)
            gurobi_model.addConstr(total_total_sum <= self.get_server_computing(n), name="constraint_2")
            # print("constraint_2", n, "finished")

    def constraint_3(self, gurobi_model, variable_x, m_list, k_list, time, epsilon: float = 0.01):
        """
        部署唯一性约束
        """
        for m, k in zip(m_list, k_list):
            for microservice_id in self.application_contain_microservice_ids(k):
                sum = 0
                microservice_base = self.find_microservice_base(m, k, list(zip(m_list, k_list))) * self.server_num
                for n in self.server_ids:
                    sum += self.find_variable_deploy(variable_x, m, k, microservice_id, n, microservice_base)
                gurobi_model.addConstr(sum == 1, name="constraint_3")

    def constraint_4(self, gurobi_model, variable_x, m_list, k_list, time, epsilon: float = 0.01):
        """
        初始微服务的约束，这个限定了某些变量的取值
        """
        for m, k in zip(m_list, k_list):
            # 有修改
            microservice_base = self.find_microservice_base(m, k, list(zip(m_list, k_list))) * self.server_num
            server_id = self.find_initial_microservice_deploy(m, k, time)
            matrix = np.zeros(self.server_num)
            matrix[server_id - 1] = 1
            gurobi_model.addConstrs((variable_x[microservice_base + i] == matrix[i] for i in range(self.server_num)), name="constraint_4")

    def find_initial_microservice_deploy(self, m, k, time):
        return self.get_device_connected_server(time, device_id=m)

    def find_variable_deploy(self, variable_x, m, k, microservice_id, server_id, microservice_base):
        """
        该函数的作用是根据给定的变量，找到给定的微服务部署在某台服务器上对应的是哪一位变量，包括了0
        """
        microservice_id_index = self.application_contain_microservice_ids(k).index(microservice_id)
        return variable_x[microservice_base + microservice_id_index * self.server_num + (server_id - 1)]

    # def Objective_function(self, gurobi_model, variable_x, m, k, epsilon:float = 0.01):
    #     """
    #     目标函数，目前考虑的是单m单k，若有额外的情况需要更改代码逻辑
    #     """
    #     Matrix_M_m_k = self.calculate_Matrix_M_m_k(m, k, epsilon=self.epsilon)
    #     Matrix_W_k = self.calculate_W_k(k, epsilon=self.epsilon)

    #     obj1 = [Matrix_M_m_k[i] * variable_x[i] for i in range(len(variable_x))]
    #     obj2 = [variable_x[i] * Matrix_W_k[i][j] * variable_x[j] for i in range(len(variable_x)) for j in range(len(variable_x))]

    #     obj = obj1 + obj2

    #     gurobi_model.setObjective(gp.quicksum(obj), GRB.MINIMIZE)

    # ------------------------多个设备同时发生移动时的情况------------------------

    def Objective_function(self, gurobi_model, variable_x, m_list, k_list, epsilon: float = 0.01):
        """
        目标函数，已经修改为多m多k时的情况，若有额外的情况需要更改代码逻辑
        """
        obj_multi = []

        if len(m_list) != len(k_list):
            raise ValueError("The number of devices is not equal to the number of applications!")

        variable_idx = 0
        for idx in range(len(m_list)):
            m = m_list[idx]
            k = k_list[idx]

            Matrix_M_m_k = self.calculate_Matrix_M_m_k(m, k, epsilon=epsilon)
            Matrix_W_k = self.calculate_W_k(k, epsilon=epsilon)

            obj1 = [Matrix_M_m_k[i] * variable_x[i + variable_idx] for i in range(len(Matrix_M_m_k))]
            obj2 = [
                variable_x[i + variable_idx] * Matrix_W_k[i][j] * variable_x[j + variable_idx]
                for i in range(len(Matrix_W_k))
                for j in range(len(Matrix_W_k))
            ]

            variable_idx += len(Matrix_M_m_k)

            obj = obj1 + obj2

            obj_multi += obj

        gurobi_model.setObjective(gp.quicksum(obj_multi), GRB.MINIMIZE)

    # --------------------------------------------------------------------------

    def gurobi_create(self, x_dim: int):
        """
        该函数的作用是创建gurobi模型
        """
        model = gp.Model()
        model.setParam("nonconvex", 2)
        x = model.addVars(int(x_dim), vtype=GRB.CONTINUOUS, name="x", lb=0, ub=1)
        if not self.output:
            model.setParam("OutputFlag", 0)

        return model, x

    def extract_action(self):
        """
        该函数的作用是从gurobi模型中提取出决策结果
        """
        action = {}
        if self.x == None or self.m_list == None or self.k_list == None:
            raise ValueError("There are problem in solving!")
        x = self.x
        for m, k in zip(self.m_list, self.k_list):
            microservice_base = self.find_microservice_base(m, k, list(zip(self.m_list, self.k_list))) * self.server_num
            microservice_ids = self.application_contain_microservice_ids(k)
            microservice_number = len(microservice_ids)
            for idx in range(microservice_number):
                if idx == 0:
                    continue
                candidate_list = [round(x[i + idx * self.server_num + microservice_base].x) for i in range(self.server_num)]
                server_id = candidate_list.index(1) + 1
                if self.microservice_deployment_last[m][k][microservice_ids[idx]] != server_id:
                    action = self.add_migrate(action, m, k, microservice_ids[idx], server_id)

        self.x = None
        self.m_list = None
        self.k_list = None
        return action

    def add_migrate(self, action: dict, device_id: int, application_id: int, microservice_id: int, server_id: int):
        if device_id not in action.keys():
            action[device_id] = {}
        if application_id not in action[device_id].keys():
            action[device_id][application_id] = {}
        action[device_id][application_id][microservice_id] = server_id
        return action

    # ------------------------求解算法的主体部分，可调用的函数------------------------
    def get_data(self, time: int):
        self.get_deployment_from_database(time - 1)
        self.get_server_deploy_microservice(time - 1)
        m_k_dict = self.get_changed_devices_and_applications(time)
        if m_k_dict == {}:
            self.pass_flag = True
            self.solve_flag = True
            return
        # 当且仅当目前这种情况才拥有的判断，当前为多设备多应用的支持的情况
        # if len(m_k_dict) != 1:
        #     raise ValueError("The number of changed devices is not 1!")

        m_list = []
        k_list = []
        for device_id in m_k_dict.keys():
            application_ids = m_k_dict[device_id]
            for application_id in application_ids:
                m_list.append(device_id)
                k_list.append(application_id)

        # if time == 24:
        #     a = 1
        #     pass

        # TODO:这里需要更改把m,k改成list的形式
        # 计算变量数量
        variable_number = 0
        for k in k_list:
            variable_number += self.server_num * (self.application_contain_microservice_number(k) + 1)

        model, x = self.gurobi_create(variable_number)
        self.constraint_1(model, x, m_list, k_list, time, epsilon=self.epsilon)
        self.constraint_2(model, x, m_list, k_list, time, epsilon=self.epsilon)
        self.constraint_3(model, x, m_list, k_list, time, epsilon=self.epsilon)
        self.constraint_4(model, x, m_list, k_list, time, epsilon=self.epsilon)
        self.Objective_function(model, x, m_list, k_list, epsilon=self.epsilon)

        self.model = model
        self.x = x
        self.m_list = m_list
        self.k_list = k_list
        self.solve_flag = True

    def solve(self):
        if self.solve_flag == False:
            raise ValueError("solve in the wrong order!")
        if self.pass_flag == True:
            self.pass_flag = False
            return {"migrate": {}}
        self.model.optimize()
        self.solve_flag = False

        action_result = self.extract_action()
        action = {"migrate": action_result}
        return action


# ------------------------辅助函数------------------------
def find_all_indices(lst, element):
    """
    找到列表中所有出现的元素的索引,约束1的辅助函数
    """
    indices = []
    for i in range(len(lst)):
        if lst[i] == element:
            indices.append(i)
    return indices
