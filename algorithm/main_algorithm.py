from database import Database
from algorithm.Random_algorithm import RandomAlgorithm
from algorithm.gurobi import GurobiAlgorithm
from algorithm.full_gurobi import FullGurobi
from algorithm.greedy_algorithm import GreedyAlgorithm

class Algorithm:
    """
    算法基类，用于实现不同的算法框架
    """
    def __init__(self, database:Database, algorithm_type:str = "base"):
        # 算法类型目前有 random和gurobi两种
        self.database = database
        if algorithm_type == "base":
            self.algorithm:RandomAlgorithm = RandomAlgorithm(self.database)
        elif algorithm_type == "gurobi":
            self.algorithm:GurobiAlgorithm = GurobiAlgorithm(self.database)
        elif algorithm_type == "fullgurobi":
            self.algorithm:FullGurobi = FullGurobi(self.database)
        elif algorithm_type == "greedy":
            self.algorithm:GreedyAlgorithm = GreedyAlgorithm(self.database)
    
    # 每个算法都需要实现下面两个方法，该方法的功能是根据给定的时间从数据库中得到系统状态，以便于求解
    def get_data(self, time:int):
        return self.algorithm.get_data(time)

    # 该方法是进行具体的求解工作
    def solve(self):
        return self.algorithm.solve()

