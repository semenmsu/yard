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
        self.sell_limit = 0
        self.current_price = 0
        self.profit_history = []
        self.store = parent.store
        self.si = self.store.subscribe(symbol, self)
        self.location = parent.location+symbol+"/"
        self.long = Order(instrument=self.si, dir=BUY)
        self.short = Order(instrument=self.si, dir=SELL)

    def update(self):
        #print("robo2 update si price = ", self.si.price)
        self.buy_price = self.si.price - 10
        self.sell_price = self.si.price + 10
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


class Nanit2:
    def __init10__(self, symbol,  parent):

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
        self.status = "stopped"

    def __init__(self, config):
        #self.type = type(self).__name__
        self.type = "Nanit"
        print("MY type!!!!!!!!!!!!!!!!!!!!!!!!", self.type)
        self.buy_price = 0
        self.buy_by = 1
        self.buy_limit = 1
        self.buy_shift = 5
        self.sell_price = 0
        self.sell_by = 1
        self.sell_limit = -1
        self.sell_shift = 5
        self.current_price = 0
        self.profit_history = []
        #self.store = parent.store
        self.name = config['name']
        self.symbol = config['symbol']
        #self.trade_instrument = self.store.subscribe(self.symbol, self)
        self.trade_instrument = None
        self.location = None
        self.long = None
        self.short = None
        #self.long = Order(instrument=self.trade_instrument , dir=BUY)
        #self.short = Order(instrument=self.trade_instrument , dir=SELL)
        self.status = "stopped"

    def get_snapshot(self):
        d = dict()
        d['type'] = self.type
        d['name'] = self.name
        d['position'] = self.position()
        d['profit'] = self.profit()
        d['status'] = self.status
        d['bid'] = self.trade_instrument.get_real_price(self.buy_price)
        d['ask'] = self.trade_instrument.get_real_price(self.sell_price)
        childs = []
        childs.append(self.long.get_snapshot())
        childs.append(self.short.get_snapshot())
        d['childs'] = childs
        d['params'] = {
            "buy_shift": {
                "value": self.buy_shift,
                "type": "int",
                "step": "1"
            },
            "sell_shift": {
                "value": self.sell_shift,
                "type": "int",
                "step": "1"
            },
            "buy_by": {
                "value": self.buy_by,
                "type": "int",
                "step": "1"
            },
            "sell_by": {
                "value": self.sell_by,
                "type": "int",
                "step": "1"
            },
            "buy_limit": {
                "value": self.buy_limit,
                "type": "int",
                "step": "1",
                "min": "0"
            },
            "sell_limit": {
                "value": self.sell_limit,
                "type": "int",
                "step": "1",
                "max": "0"
            }
        }
        return d

    def get_config(self):
        d = dict()
        d['name'] = self.name
        d['type'] = self.type
        d['symbol'] = self.symbol
        d['buy_limit'] = self.buy_limit
        d['buy_by'] = self.buy_by
        d['sell_limit'] = self.sell_limit
        d['sell_by'] = self.sell_by
        return d

    def get_state(self):
        d = dict()
        d['position'] = self.position()
        d['profit'] = self.profit()
        d['long'] = self.long.get_state()
        d['short'] = self.short.get_state()
        return d

    # lazy initialization

    def add_to_parent(self, parent):
        if not self.trade_instrument:
            self.parent = parent
            self.store = parent.store
            self.trade_instrument = self.store.subscribe(self.symbol, self)
            self.long = Order(instrument=self.trade_instrument, dir=BUY)
            self.short = Order(instrument=self.trade_instrument, dir=SELL)
        else:
            raise f"add nanit twice {self.symbol}"

    def set_status(self, status):
        self.status = status

    def control(self, control_command):
        cmd = control_command.command()
        if cmd == "start":
            self.status = "running"
        elif cmd == "stop":
            self.status = "stopped"
        elif cmd == "params":
            param_name = control_command.message['param']
            param_value = control_command.message['value']
            if param_name and param_value:
                if param_name == "buy_shift":
                    self.buy_shift = int(param_value)
                elif param_name == "sell_shift":
                    self.sell_shift = int(param_value)
                elif param_name == "buy_by":
                    self.buy_by = int(param_value)
                elif param_name == "sell_by":
                    self.sell_by = int(param_value)
                elif param_name == "buy_limit":
                    self.buy_limit = int(param_value)
                elif param_name == "sell_limit":
                    self.sell_limit = int(param_value)

    def update(self):

        #print("robo2 update si price = ", self.si.price)
        self.buy_price = self.trade_instrument.price - \
            self.buy_shift*self.trade_instrument.min_step_price_i
        self.sell_price = self.trade_instrument.price + \
            self.sell_shift*self.trade_instrument.min_step_price_i
        # self.current_price = self.trade_instrument.get_real_price(
        #    self.trade_instrument.price)
        self.current_price = self.trade_instrument.price
        buy_amount = self.buy_by
        sell_amount = self.sell_by

        if self.buy_limit <= self.position():
            buy_amount = 0

        if self.sell_limit >= self.position():
            sell_amount = 0

        if self.status == "running":
            #print("i'm running")
            if self.long.should_update_price(self.buy_price, buy_amount):
                # rewrite up to root
                data = DataOrderEvent(self.buy_price, buy_amount)
                yield from self.long.do2(data)

            if self.short.should_update_price(self.sell_price, sell_amount):
                data = DataOrderEvent(self.sell_price, sell_amount)
                yield from self.short.do2(data)
        elif self.status == "stopped":
            buy_amount = 0
            sell_amount = 0
            if self.long.should_update_price(self.buy_price, buy_amount):
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
