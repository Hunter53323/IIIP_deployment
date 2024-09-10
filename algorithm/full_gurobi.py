# 使用gurobi进行全局求解的办法
from database import Database
from algorithm.gurobi import GurobiAlgorithm
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import time

class FullGurobi(GurobiAlgorithm):
    def __init__(self, database:Database):
        self.database = database
        self.SCA_flag = False
        self.output = False
        self.time = None

        self.M = None
        self.W = None
        self.Q = None
        self.b = None
        self.Y = None
        self.S = None
        self.G = None
        self.C_S = None
        self.C_C = None
        self.H = None
        self.VG = None
        self.x_dim = None
        self.d_dim = None
        self.P_SCA = None
        self.N_SCA = None
        self.para_dict = None
    
    def __matrix_K(self, time):
        """应用程序（转义）数量"""
        actual_K_id = []
        actual_device_id = []
        count = 0
        for device_id in self.device_ids:
            device_requests = self.device_request(device_id, time)
            for app_id in device_requests:
                actual_K_id.append(app_id)
                actual_device_id.append(device_id)
                count += 1
        return count, actual_K_id, actual_device_id

    def __matrix_N(self):
        """服务器数量"""
        return self.server_num
    
    def __matrix_C_S(self):
        """服务器存储"""
        C_S = []
        for server_id in self.server_ids:
            C_S.append(self.get_server_storage(server_id))
        return np.array(C_S).transpose()
    
    def __matrix_C_C(self):
        """服务器计算"""
        C_C = []
        for server_id in self.server_ids:
            C_C.append(self.get_server_computing(server_id))
        return np.array(C_C).transpose()
    
    def __matrix_b_cloud(self):
        """与云的带宽"""
        b_cloud = []
        for server_id in self.server_ids:
            b_cloud.append(self.get_server_bandwidth(server_id))
        return np.array(b_cloud)
    
    def __matrix_A(self, time):
        """每个应用程序k的微服务数量""" 
        A = []
        for device_id in self.device_ids:
            device_requests = self.device_request(device_id, time)
            for app_id in device_requests:
                A.append(self.application_contain_microservice_number(app_id))
        A = [x+1 for x in A]
        return np.array(A)
    
    def __matrix_L(self):
        """微服务包含的层的数量"""
        L = len(self.microservice_library)
        return L
    
    def __matrix_E_kil(self, K, L, A, K_id_list):
        """每个应用程序k的微服务i所包含的l层,包括初始微服务"""
        E_kil = []
        for k in range(K):
            ms_number = A[k]
            K_id = K_id_list[k]
            ms_ids = self.application_contain_microservice_ids(K_id)
            e_kil = np.zeros((ms_number, L))
            for ms in range(1,ms_number):
                ms_id = ms_ids[ms]
                e_kil[ms, ms_id] = 1
            E_kil.append(e_kil)
        return E_kil

    
    def __matrix_S_l(self):
        """微服务包含的层的大小,这里每个微服务的所有层都变成1层，列表指数为微服务id减一"""
        S_l = [0]*len(self.microservice_library)
        for microservice_id in self.microservice_library:
            S_l[microservice_id-1] = self.get_microservice_size(microservice_id)
        S_l = np.atleast_2d(np.array(S_l)).transpose()
        return S_l
    
    def __matrix_u(self, K, A, K_id_list):
        """每个微服务的计算能力"""
        u = []
        
        for k in range(K):
            u_k = []
            K_id = K_id_list[k]
            ms_ids = self.application_contain_microservice_ids(K_id)
            for ms in range(A[k]):
                if ms == 0:
                    u_k.append(0)
                    continue
                microservice_id = ms_ids[ms]
                u_k.append(self.get_microservice_cpu(microservice_id))
            u.append(np.array(u_k).transpose())
        return u

    def __matrix_w(self, K, A, K_id_list):
        """微服务之间的通讯开销"""
        w = []
        for k in range(K):
            K_id = K_id_list[k]
            ms_ids = self.application_contain_microservice_ids(K_id)
            w_k = np.zeros((A[k],A[k]))
            for ms_1 in ms_ids:
                for ms_2 in ms_ids:
                    ms_1_index = ms_ids.index(ms_1)
                    ms_2_index = ms_ids.index(ms_2)
                    w_k[ms_1_index, ms_2_index] = self.get_communication(K_id, ms_1, ms_2)
            w.append(w_k)
        return w
    
    def __matrix_D(self):
        """多跳路径"""
        return self.matrix_D
    
    def __matrix_Source(self, K, Device_id_list, time):
        """源节点"""
        Source = []
        for k in range(K):
            device_id = Device_id_list[k]
            Source.append(self.get_device_connected_server(time, device_id)-1)
        return Source
    
    def collect_parameters(self, time):
        K, K_id_list, Device_id_list = self.__matrix_K(time)
        N = self.__matrix_N()
        C_S = self.__matrix_C_S()
        C_C = self.__matrix_C_C()
        b_cloud = self.__matrix_b_cloud()
        A = self.__matrix_A(time)
        L = self.__matrix_L()
        E_kil = self.__matrix_E_kil(K, L, A, K_id_list)
        S_l = self.__matrix_S_l()
        u = self.__matrix_u(K, A, K_id_list)
        w = self.__matrix_w(K, A, K_id_list)
        D = self.__matrix_D()
        Source = self.__matrix_Source(K, Device_id_list, time)

        para_dict = {}
        para_dict["K"] = K
        para_dict["N"] = N
        para_dict["C_S"] = C_S
        para_dict["C_C"] = C_C
        para_dict["A"] = A
        para_dict["L"] = L
        para_dict["E_kil"] = E_kil
        para_dict["S_l"] = S_l
        para_dict["u"] = u
        para_dict["w"] = w
        para_dict["D"] = D
        para_dict["b_cloud"] = b_cloud
        para_dict["Source"] = Source

        return K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source,para_dict
    
    def matrix_calculate(self, K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source, para_dict, SCA = False):
        """根据参数计算相关矩阵"""
        D_size = np.shape(D)[0]

        x_dim = sum(A)*N
        d_dim = N*L

        W_k = []
        for k in range(K):
            D_big = np.tile(D, (A[k], A[k]))
            w_k = np.zeros((A[k]*D_size, A[k]*D_size))
            for i in range(A[k]):
                for j in range(A[k]):
                    w_k[i*D_size:(i+1)*D_size, j*D_size:(j+1)*D_size] = w[k][i][j]

            W_k.append(w_k*D_big)

        q = np.ones((1,N))
        Q_k = []
        for k in range(K):
            blk = []
            for i in range(A[k]):
                blk = blkdiag(blk, q)
            Q_k.append(blk)

        P = []
        for k in range(K):
            P_k = []
            for n in range(N):
                p_N_n = p_m_n(N,n)
                blk = []
                for i in range(A[k]):
                    blk = blkdiag(blk, p_N_n)
                P_k.append(blk)
            P.append(P_k)

        V = []
        for k in range(K):
            V_k = []
            for l in range(L):
                p_L_n = p_m_n(L,l).transpose()
                blk = []
                for i in range(A[k]):
                    blk = blkdiag(blk, p_L_n)
                V_k.append(blk)
            V.append(V_k)

        E = []
        for k in range(K):
            E_k = np.zeros((L*A[k],1))
            for i in range(A[k]):
                E_k[i*L:(i+1)*L] = np.atleast_2d(E_kil[k][i]).transpose()
            E.append(E_k)

        # 定义最后的大矩阵
        M = []
        for n in range(N):
            M = hstack(M, S_l.transpose()/b_cloud[n])

        W = []
        for k in range(K):
            W = blkdiag(W, W_k[k])

        b = np.ones((sum(A),1))

        Q = []
        for k in range(K):
            Q = blkdiag(Q, Q_k[k])

        Y_n = []
        for n in range(N):
            mid_M = []
            for k in range(K):
                mid_m = []
                for l in range(L):
                    mid_m = hstack(mid_m,  P[k][n].dot(V[k][l]).dot(E[k]))
                mid_M = vstack(mid_M, mid_m)
            Y_n.append(mid_M)

        G_n = []
        for n in range(N):
            mid = []
            for k in range(K):
                mid = vstack(mid, np.atleast_2d(P[k][n].dot(u[k])).transpose())
            G_n.append(mid)

        G = []
        for n in range(N):
            G = hstack(G, G_n[n])
        G = G.transpose()

        Y = []
        for n in range(N):
            Y = hstack(Y, Y_n[n])
        Y = Y.transpose()


        S = []
        for n in range(N):
            S = blkdiag(S, S_l)
        S = S.transpose()

        #虚拟微服务的定义
        VG= []
        for k in range(K):
            VG_k = p_m_n(N,Source[k])
            VG = vstack(VG, VG_k)

        eye_n = np.eye(N)
        zero_n = np.zeros((N,N))
        H_k = []
        for k in range(K):
            mid = []
            for i in range(A[k]):
                if i == 0:
                    mid = eye_n
                else:
                    mid = hstack(mid, zero_n)
            H_k.append(mid)

        H = []
        for k in range(K):
            H = blkdiag(H, H_k[k])

        P_SCA = 0
        N_SCA = 0

        if SCA:
            W = W + W.T
            W_size = np.shape(W)[0]
            eig_w = np.linalg.eig(W)
            max_eig = max(abs(eig_w[0]))
            P_SCA = W + max_eig*np.eye(W_size)
            N_SCA = max_eig*np.eye(W_size)
            W = W/2

        para_dict["M"] = M
        para_dict["W"] = W
        para_dict["Q"] = Q
        para_dict["b"] = b
        para_dict["Y"] = Y
        para_dict["S"] = S
        para_dict["G"] = G
        para_dict["H"] = H
        para_dict["VG"] = VG
        para_dict["x_dim"] = x_dim
        para_dict["d_dim"] = d_dim
        para_dict["b"] = b
        para_dict["P_SCA"] = P_SCA
        para_dict["N_SCA"] = N_SCA

        return M,W,Q,b,Y,S,G,C_S,C_C,H,VG,x_dim,d_dim,P_SCA,N_SCA,para_dict
    
    def set_SCA_flag(self, flag:bool):
        self.SCA_flag = flag

    def gurobi_solve(self):
        start = time.perf_counter()
        opt = 0 # 优化目标是求解通讯开销还是下载延迟还是两个都有
        # theta = 0.5
        theta = 0.1
        T_max = 1
        T_min = 0
        R_max = 1
        R_min = 0

        K,N,M,W,Q,b,Y,S,G,C_S,C_C,H,VG,x_dim,d_dim,P_SCA,N_SCA,para_dict = self.K,self.N,self.M,self.W,self.Q,self.b,self.Y,self.S,self.G,self.C_S,self.C_C,self.H,self.VG,self.x_dim,self.d_dim,self.P_SCA,self.N_SCA,self.para_dict
        if self.SCA_flag:
            x_last = np.zeros(int(x_dim))
            epsilon = 100
            SCA_num = 20

        # 初始化Gurobi
        model = gp.Model()
        if self.SCA_flag == True or self.output == False:
            model.setParam('OutputFlag', 0)

        model.setParam('nonconvex', 2)
        x = model.addVars(int(x_dim), vtype=GRB.BINARY, name='x')
        d = model.addVars(int(d_dim), vtype=GRB.BINARY, name='d')
        # x = model.addVars(int(x_dim), vtype=GRB.CONTINUOUS, name='x')
        # d = model.addVars(int(d_dim), vtype=GRB.CONTINUOUS, name='d')

        # 添加约束
        model.addConstrs(gp.quicksum(Q[i][j]*x[j] for j in range(x_dim)) == b[i][0] for i in range(b.size))
        model.addConstrs(gp.quicksum(H[i][j]*x[j] for j in range(x_dim)) == VG[i][0] for i in range(len(VG)))
        model.addConstrs(gp.quicksum(Y[i][j]*x[j] for j in range(x_dim)) >= d[i] for i in range(d_dim))
        model.addConstrs(gp.quicksum(Y[i][j]*x[j]/10 for j in range(x_dim)) <= d[i] for i in range(d_dim))
        model.addConstrs(gp.quicksum(S[i][j]*d[j] for j in range(d_dim)) <= C_S[i] for i in range(C_S.size))
        model.addConstrs(gp.quicksum(G[i][j]*x[j] for j in range(x_dim)) <= C_C[i] for i in range(C_C.size))

        # if get_max_min == True:
        #     #minmax的第一步
        #     obj = [x[i]*x[j]*W[i][j] for i in range(x_dim) for j in range(x_dim)]
        #     model.setObjective(gp.quicksum(obj), GRB.MINIMIZE)
        #     print("开始求解第一个最大最小值")
        #     model.optimize()
        #     print("求解完成")

        #     T_max = sum([d[i].x*float(M[0][i]) for i in range(d_dim)])
        #     R_min = sum([x[i].x*x[j].x*W[i][j] for i in range(x_dim) for j in range(x_dim)])

        #     #minmax的第二步
        #     obj = [d[i]*float(M[0][i]) for i in range(d_dim)]
        #     model.setObjective(gp.quicksum(obj), GRB.MINIMIZE)
        #     print("开始求解第二个最大最小值")
        #     model.optimize()
        #     print("求解完成")

        #     T_min = sum([d[i].x*float(M[0][i]) for i in range(d_dim)])
        #     R_max = sum([x[i].x*x[j].x*W[i][j] for i in range(x_dim) for j in range(x_dim)])

        Tconst1 = theta/(T_max - T_min)
        Tconst2 = float(theta*T_min)/(T_max - T_min)
        Rconst1 = (1-theta)/(R_max - R_min)
        Rconst2 = float((1-theta)*R_min)/(R_max - R_min)

        obj = []
        if opt == 0 or opt == 1:
            for i in range(int(x_dim)):
                for j in range(int(x_dim)):
                    if self.SCA_flag == False:
                        obj.append(0.1*Rconst1 * x[i]*x[j]*W[i][j])
                    else:
                        obj.append(Rconst1 * 0.5 * x[i]*x[j]*P_SCA[i][j])
                        obj.append(Rconst1 * (-1) * x_last[i]*x[j]*N_SCA[i][j])
        if opt == 0 or opt == 2:
            for i in range(int(d_dim)):
                    obj.append(Tconst1 * d[i]*float(M[0][i]))
        model.setObjective(gp.quicksum(obj), GRB.MINIMIZE)
        print("开始优化")
        model.optimize()

        end = time.perf_counter()

        x_res = []
        for i in range(int(x_dim)):
            x_res.append(x[i].x)

        d_res = []
        for i in range(int(d_dim)):
            d_res.append(d[i].x)

        deployment,_,_,_ = decoder(x_res,K,N,para_dict)
        print("solve time:", end-start,"s")

        return deployment

    def extract_action(self, deployment):
        """从得出的求解动作中把需要改变的微服务的信息提取出来"""
        K, K_id_list, Device_id_list = self.__matrix_K(self.time)

        action = {}
        for k in range(K):
            device_id = Device_id_list[k]
            application_id = K_id_list[k]
            microservice_ids = self.application_contain_microservice_ids(application_id)
            for i in range(1,len(microservice_ids)):
                microservice_id = microservice_ids[i]
                if deployment[k][i] != self.microservice_deployment_last[device_id][application_id][microservice_id]:
                    action = self.add_migrate(action, device_id, application_id, microservice_id, deployment[k][i])

        self.M = None
        self.W = None
        self.Q = None
        self.b = None
        self.Y = None
        self.S = None
        self.G = None
        self.C_S = None
        self.C_C = None
        self.H = None
        self.VG = None
        self.x_dim = None
        self.d_dim = None
        self.P_SCA = None
        self.N_SCA = None
        self.para_dict = None

        return action
    
    def get_data(self, time:int):
        self.time = time
        self.get_deployment_from_database(time-1)
        K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source,para_dict = self.collect_parameters(time)
        M,W,Q,b,Y,S,G,C_S,C_C,H,VG,x_dim,d_dim,P_SCA,N_SCA,para_dict = self.matrix_calculate(K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source, para_dict, SCA = self.SCA_flag)

        self.K = K
        self.N = N
        self.M = M
        self.W = W
        self.Q = Q
        self.b = b
        self.Y = Y
        self.S = S
        self.G = G
        self.C_S = C_S
        self.C_C = C_C
        self.H = H
        self.VG = VG
        self.x_dim = x_dim
        self.d_dim = d_dim
        self.P_SCA = P_SCA
        self.N_SCA = N_SCA
        self.para_dict = para_dict

    
    def solve(self):
        deployment = self.gurobi_solve()
        action_result = self.extract_action(deployment)

        action = {"migrate":action_result}
        return action
    
    def first_deploy(self):
        """第一次部署"""
        K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source,para_dict = self.collect_parameters(0)
        M,W,Q,b,Y,S,G,C_S,C_C,H,VG,x_dim,d_dim,P_SCA,N_SCA,para_dict = self.matrix_calculate(K,N,C_S,C_C,A,L,E_kil,S_l,u,w,D,b_cloud,Source, para_dict, SCA = self.SCA_flag)
        self.K = K
        self.N = N
        self.M = M
        self.W = W
        self.Q = Q
        self.b = b
        self.Y = Y
        self.S = S
        self.G = G
        self.C_S = C_S
        self.C_C = C_C
        self.H = H
        self.VG = VG
        self.x_dim = x_dim
        self.d_dim = d_dim
        self.P_SCA = P_SCA
        self.N_SCA = N_SCA
        self.para_dict = para_dict

        deployment = self.gurobi_solve()

        K, K_id_list, Device_id_list = self.__matrix_K(0)
        action = {}
        for k in range(K):
            device_id = Device_id_list[k]
            application_id = K_id_list[k]
            microservice_ids = self.application_contain_microservice_ids(application_id)
            for i in range(1,len(microservice_ids)):
                microservice_id = microservice_ids[i]
                action = self.add_migrate(action, device_id, application_id, microservice_id, deployment[k][i])
        actions = {"deploy":action}

        self.M = None
        self.W = None
        self.Q = None
        self.b = None
        self.Y = None
        self.S = None
        self.G = None
        self.C_S = None
        self.C_C = None
        self.H = None
        self.VG = None
        self.x_dim = None
        self.d_dim = None
        self.P_SCA = None
        self.N_SCA = None
        self.para_dict = None

        return actions

def decoder(x,K,N,para_dict):
    A = para_dict['A']
    L = para_dict['L']
    E_kil = para_dict['E_kil']

    d_ori = np.zeros((N,L))
    A_dim = N*sum(A)
    x_fix = np.zeros((A_dim,1))

    deployment = []

    count_ms = 0
    for k in range(K):
        deployment_k = np.zeros(A[k])
        for i in range(A[k]):
            det_v = x[count_ms*N:(count_ms+1)*N]
            n = np.argmax(det_v)
            deployment_k[i] = n+1
            x_fix[count_ms*N+n-1]=1
            d_ori[n] += E_kil[k][i]
            count_ms += 1
        deployment.append(deployment_k)

    d_fix = np.zeros((N,L))
    d_fix = np.where(d_ori>0.9,1,d_fix)

    return deployment,x_fix,d_ori,d_fix
    
def blkdiag(a,b):
    """
    将输入的矩阵构造为分块对角矩阵
    """
    if not len(a):
        return b
    elif not len(b):
        return a
    a_shape = np.atleast_2d(a)
    b_shape = np.atleast_2d(b)
    return np.block([
        [a, np.zeros((a_shape.shape[0],b_shape.shape[1]))], 
        [np.zeros((b_shape.shape[0],a_shape.shape[1])), b]])

def p_m_n(m,n):
    # 该函数的作用是构造通用列向量p_m_n，向量长度为m，第n位为1，其余都为0
    p = np.zeros((m,1))
    p[n] = 1
    return p

def hstack(a,b):
    if not len(a):
        return b
    elif not len(b):
        return a
    return np.hstack((a,b))

def vstack(a,b):
    if not len(a):
        return b
    elif not len(b):
        return a
    return np.vstack((a,b))