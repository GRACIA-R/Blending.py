# optimizer.py
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

class WaterBlendOptimizer:

    def __init__(self, df, w_As=0.3, w_Cl=0.2, As_ref=0.025, Cl_ref=320):
        self.df = df.copy()
        self.w_As = w_As
        self.w_Cl = w_Cl
        self.As_ref = As_ref
        self.Cl_ref = Cl_ref
        self._compute_scores()

    def _compute_scores(self):
        self.df["score"] = (
            self.w_As * (self.df["As"] / self.As_ref) +
            self.w_Cl * (self.df["Cl"] / self.Cl_ref)
        ) / (self.df["avail"] + 1e-6)

    def optimize(self, demand):

        Qmax_available = (self.df["Qmax"] * self.df["avail"]).sum()
        if demand > Qmax_available:
            raise ValueError("La demanda supera la capacidad disponible")

        prob = LpProblem("WaterBlending", LpMinimize)

        Q = {
            p: LpVariable(f"Q_{p}", 0, self.df.loc[p, "Qmax"])
            for p in self.df.index
        }

        prob += lpSum(Q[p] * self.df.loc[p, "score"] for p in self.df.index)
        prob += lpSum(Q[p] for p in self.df.index) == demand

        prob.solve(PULP_CBC_CMD(msg=False))

        Q_opt = {p: Q[p].value() for p in self.df.index}

        Qt = sum(Q_opt.values())
        As_final = sum(Q_opt[p] * self.df.loc[p, "As"] for p in self.df.index) / Qt
        Cl_final = sum(Q_opt[p] * self.df.loc[p, "Cl"] for p in self.df.index) / Qt

        return Q_opt, As_final, Cl_final
