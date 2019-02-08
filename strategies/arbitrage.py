import strategies.__before__
from algo.nanit import *


class Arbitrage:
    def __init__(self, parent):
        self.store = parent.store
        self.parent = parent
        self.uniq_name = "arbitrage"
        self.location = parent.location+"arbitrage/"
        self.si = self.store.subscribe("Si-3.19", self)
        self.rts = self.store.subscribe("RTS-3.19", self)
        self.n_si = Nanit(self.si.symbol, parent=self)
        self.n_rts = Nanit(self.rts.symbol, parent=self)
        self.profit_history = []
        self.need_update = False

    def update(self):
        yield

    def position(self):
        pos = dict()
        pos[self.si.symbol] = self.n_si.position()
        pos[self.rts.symbol] = self.n_rts.position()

    def profit(self):
        return self.n_si.profit() + self.n_rts.profit()
