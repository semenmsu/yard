from algo.utils import *
from algo.order import Order
from algo.events import DataOrderEvent


class Nanit:
    def __init__(self, symbol,  parent):

        #mount(self, self.long)
        #mount(self, self.short)
        self.buy_price = 0
        self.buy_by = 1
        self.buy_limit = 1
        self.sell_price = 0
        self.sell_by = 1
        self.sell_limit = -4
        self.current_price = 0
        self.profit_history = []
        self.store = parent.store
        self.si = self.store.subscribe(symbol, self)
        self.location = parent.location+symbol+"/"
        self.long = Order(instrument=self.si, dir=BUY)
        self.short = Order(instrument=self.si, dir=SELL)

    def update(self):
        #print("robo2 update si price = ", self.si.price)
        self.buy_price = self.si.price - 6
        self.sell_price = self.si.price + 4
        self.current_price = self.si.price
        buy_amount = self.buy_by
        sell_amount = self.sell_by

        if self.buy_limit <= self.position():
            buy_amount = 0

        if self.sell_limit >= self.position():
            sell_amount = 0

        if self.long.should_update_price(self.buy_price, buy_amount):
            # rewrite up to root
            data = DataOrderEvent(self.buy_price, buy_amount)
            yield from self.long.do2(data)

        if self.short.should_update_price(self.sell_price, sell_amount):
            data = DataOrderEvent(self.sell_price, sell_amount)
            yield from self.short.do2(data)

    def position(self):
        return self.long.total_trades - self.short.total_trades

    def profit(self):
        money = -self.long.total_money + self.short.total_money
        profit = money + self.position()*self.current_price
        return profit
