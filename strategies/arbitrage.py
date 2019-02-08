import strategies.__before__
from algo.nanit import *


class Arbitrage:
    def __init__(self, store):
        self.store = store
        self.si = store.subscribe("Si-3.19", self)
        self.rts = store.subscribe("RTS-3.19", self)
        self.n_si = Nanit(self.si.symbol, store=store)
        self.n_rts = Nanit(self.rts.symbol, store=store)
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
