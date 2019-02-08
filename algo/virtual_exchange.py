
from sortedcontainers import SortedDict
from sortedcontainers import SortedSet
from collections import deque
import numpy as np
from algo.order import *
from algo.events import *


class Exchange:
    def __init__(self):
        self.markets = dict()
        self.on_data = None
        self.on_trades = None
        self.current_order_id = 1000

    def add_market(self, market):
        self.markets[market.symbol] = market
        market.on_data = self.data_handler
        market.on_trades = self.trades_handler

    def apply_raw_order(self, order):
        if isinstance(order, NewOrder):
            self.current_order_id += 1
            order.order_id = self.current_order_id
        self.markets[order.symbol].apply_raw_order(order)

    def data_handler(self, price, symbol):
        self.on_data(price, symbol)
    
    def trades_handler(self, reply):
        self.on_trades(reply)

    def on(self, event, func):
        if event == 'data':
            self.on_data = func
        if event == 'trades':
            self.on_trades = func

    def step(self):
        for symbol, market in self.markets.items():
            market.step()


    
class Market:
    def __init__(self, initial_price=0, symbol = None):
        # self.quote_generator
        self.buy_orders = SortedSet(key=lambda x: (x.price, -x.order_id))  # -1
        self.sell_orders = SortedSet(key=lambda x: (x.price, x.order_id))  # 0
        self.orders = dict()
        self.trades = deque()
        self.price = initial_price
        self.std = 4.0
        self.mu = 0.0
        self.trade_std = 6.0
        self.history = []
        self.trade_p = np.random.binomial(1, 0.2, 1000)
        self.on_data = None
        self.on_trades = None
        self.current_order_id = 1000
        self.symbol = symbol

        def simulate_trade():
            should_simulate_trade = np.random.choice(self.trade_p)
            if should_simulate_trade:
                return np.int(np.random.normal(0.0, self.trade_std))

            return None

        self.simulate_trade = simulate_trade

        def get_buy_index(price, order_id):
            order_id = -order_id
            index = self.buy_orders.bisect_key_left((price, order_id))
            if index == len(self.buy_orders):
                return -1
            order = self.buy_orders[index]
            if price == order.price and -order_id == order.order_id:
                return index
            return -1

        def get_sell_index(price, order_id):
            index = self.sell_orders.bisect_key_left((price, order_id))
            if index == len(self.sell_orders):
                return -1
            order = self.sell_orders[index]
            if price == order.price and order_id == order.order_id:
                return index
            return -1

        self.buy_orders.get_index = get_buy_index
        self.sell_orders.get_index = get_sell_index

    def add(self, order):
        self.orders[order.order_id] = order
        if order.dir == 1:
            self.buy_orders.add(order)
        else:
            self.sell_orders.add(order)

    def remove(self, order_id):
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.dir == 1:
                idx = self.buy_orders.get_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find buy_order with order_id {order_id}")
                amount = self.buy_orders[idx].amount
                del self.buy_orders[idx]
                del self.orders[order_id]
                return amount
            else:
                idx = self.sell_orders.get_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find sell_order with order_id {order_id}")
                amount = self.sell_orders[idx].amount
                del self.sell_orders[idx]
                del self.orders[order_id]
                return amount

        return -1

    def apply_raw_order(self, order):
        if self.on_trades:
            if isinstance(order, NewOrder):
                #self.current_order_id +=1
                #order.order_id = self.current_order_id
                self.add(order)
                reply = NewReplyEvent(0, order.order_id)
                reply.ext_id = order.ext_id
                
                self.on_trades(reply)
            elif isinstance(order, CancelOrder):
                amount = self.remove(order.order_id)
                if amount > 0:
                    reply = CancelReplyEvent(0, amount)
                    reply.order_id = order.order_id
                    self.on_trades(reply)
                else:
                    reply = CancelReplyEvent(14, 0)
                    reply.order_id = order.order_id
                    self.on_trades(reply)

        pass

    def match_trade(self, price, amount, dir):
        if dir == 1:  # check sell
            while len(self.sell_orders) > 0 and self.sell_orders[0].price <= price and amount > 0:
                if self.sell_orders[0].amount >= amount:
                    self.sell_orders[0].amount -= amount
                    #print("new buy trade amount = ", amount,
                    #      "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)
                    
                    self.on_trades(trade)
                    amount = 0
                    if self.sell_orders[0].amount == 0:
                        self.remove(self.sell_orders[0].order_id)
                else:
                    #print("new buy trade amount = ",
                    #      self.sell_orders[0].amount, "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        self.sell_orders[0].amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)
                    amount -= self.sell_orders[0].amount
                    self.remove(self.sell_orders[0].order_id)

        else:
            while len(self.buy_orders) > 0 and self.buy_orders[-1].price >= price and amount > 0:
                if self.buy_orders[-1].amount >= amount:
                    self.buy_orders[-1].amount -= amount
                    #print("new sell trade amount = ", amount,
                    #      "price=", self.buy_orders[-1].price)
                    
                    trade = TradeReplyEvent(
                        amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)

                    amount = 0
                    if self.buy_orders[-1].amount == 0:
                        self.remove(self.buy_orders[-1].order_id)
                else:
                    #print("new sell trade amount = ",
                    #      self.buy_orders[-1].amount, "price=", self.buy_orders[-1].price)
                    trade = TradeReplyEvent(
                        self.buy_orders[-1].amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)
                    amount -= self.buy_orders[-1].amount
                    self.remove(self.buy_orders[-1].order_id)

    def show(self):
        for item in self.buy_orders:
            print(item)
        print("---")
        for item in self.sell_orders:
            print(item)
        print()

    def read_trades(self):
        while len(self.trades):
            trade = self.trades.popleft()
            #print(trade)

    def read_orders(self, orders):
        if isinstance(orders, list):
            for order in orders:
                self.add(order)
        else:
            self.add(orders)

    def step(self):
        simulate_trade_delta_price = self.simulate_trade()
        if simulate_trade_delta_price:
            dir = 1
            if simulate_trade_delta_price < 0:
                dir = 2

            self.match_trade(self.price + simulate_trade_delta_price, 1, dir)

        self.price += np.int(np.random.normal(self.mu+0.001, self.std))
        self.history.append(self.price)
        if self.on_data:
            self.on_data(self.price, self.symbol)

    def on(self, event, func):
        if event == 'data':
            self.on_data = func
        if event == 'trades':
            self.on_trades = func


'''
class Exchange2:

    def __init__(self, initial_price=0, symbol = None):
        # self.quote_generator
        self.buy_orders = SortedSet(key=lambda x: (x.price, -x.order_id))  # -1
        self.sell_orders = SortedSet(key=lambda x: (x.price, x.order_id))  # 0
        self.orders = dict()
        self.trades = deque()
        self.price = initial_price
        self.std = 4.0
        self.mu = 0.0
        self.trade_std = 6.0
        self.history = []
        self.trade_p = np.random.binomial(1, 0.2, 1000)
        self.on_data = None
        self.on_trades = None
        self.current_order_id = 1000
        self.symbol = symbol

        def simulate_trade():
            should_simulate_trade = np.random.choice(self.trade_p)
            if should_simulate_trade:
                return np.int(np.random.normal(0.0, self.trade_std))

            return None

        self.simulate_trade = simulate_trade

        def get_buy_index(price, order_id):
            order_id = -order_id
            index = self.buy_orders.bisect_key_left((price, order_id))
            if index == len(self.buy_orders):
                return -1
            order = self.buy_orders[index]
            if price == order.price and -order_id == order.order_id:
                return index
            return -1

        def get_sell_index(price, order_id):
            index = self.sell_orders.bisect_key_left((price, order_id))
            if index == len(self.sell_orders):
                return -1
            order = self.sell_orders[index]
            if price == order.price and order_id == order.order_id:
                return index
            return -1

        self.buy_orders.get_index = get_buy_index
        self.sell_orders.get_index = get_sell_index

    def add(self, order):
        self.orders[order.order_id] = order
        if order.dir == 1:
            self.buy_orders.add(order)
        else:
            self.sell_orders.add(order)

    def remove(self, order_id):
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.dir == 1:
                idx = self.buy_orders.get_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find buy_order with order_id {order_id}")
                amount = self.buy_orders[idx].amount
                del self.buy_orders[idx]
                del self.orders[order_id]
                return amount
            else:
                idx = self.sell_orders.get_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find sell_order with order_id {order_id}")
                amount = self.sell_orders[idx].amount
                del self.sell_orders[idx]
                del self.orders[order_id]
                return amount

        return -1

    def apply_raw_order(self, order):
        if self.on_trades:
            if isinstance(order, NewOrder):
                self.current_order_id +=1
                order.order_id = self.current_order_id
                self.add(order)
                reply = NewReplyEvent(0, order.order_id)
                reply.ext_id = order.ext_id
                
                self.on_trades(reply)
            elif isinstance(order, CancelOrder):
                amount = self.remove(order.order_id)
                if amount > 0:
                    reply = CancelReplyEvent(0, amount)
                    reply.order_id = order.order_id
                    self.on_trades(reply)
                else:
                    reply = CancelReplyEvent(14, 0)
                    reply.order_id = order.order_id
                    self.on_trades(reply)

        pass

    def match_trade(self, price, amount, dir):
        if dir == 1:  # check sell
            while len(self.sell_orders) > 0 and self.sell_orders[0].price <= price and amount > 0:
                if self.sell_orders[0].amount >= amount:
                    self.sell_orders[0].amount -= amount
                    #print("new buy trade amount = ", amount,
                    #      "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)
                    
                    self.on_trades(trade)
                    amount = 0
                    if self.sell_orders[0].amount == 0:
                        self.remove(self.sell_orders[0].order_id)
                else:
                    #print("new buy trade amount = ",
                    #      self.sell_orders[0].amount, "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        self.sell_orders[0].amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)
                    amount -= self.sell_orders[0].amount
                    self.remove(self.sell_orders[0].order_id)

        else:
            while len(self.buy_orders) > 0 and self.buy_orders[-1].price >= price and amount > 0:
                if self.buy_orders[-1].amount >= amount:
                    self.buy_orders[-1].amount -= amount
                    #print("new sell trade amount = ", amount,
                    #      "price=", self.buy_orders[-1].price)
                    
                    trade = TradeReplyEvent(
                        amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)

                    amount = 0
                    if self.buy_orders[-1].amount == 0:
                        self.remove(self.buy_orders[-1].order_id)
                else:
                    #print("new sell trade amount = ",
                    #      self.buy_orders[-1].amount, "price=", self.buy_orders[-1].price)
                    trade = TradeReplyEvent(
                        self.buy_orders[-1].amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    self.on_trades(trade)
                    amount -= self.buy_orders[-1].amount
                    self.remove(self.buy_orders[-1].order_id)

    def show(self):
        for item in self.buy_orders:
            print(item)
        print("---")
        for item in self.sell_orders:
            print(item)
        print()

    def read_trades(self):
        while len(self.trades):
            trade = self.trades.popleft()
            #print(trade)

    def read_orders(self, orders):
        if isinstance(orders, list):
            for order in orders:
                self.add(order)
        else:
            self.add(orders)

    def step(self):
        simulate_trade_delta_price = self.simulate_trade()
        if simulate_trade_delta_price:
            dir = 1
            if simulate_trade_delta_price < 0:
                dir = 2

            self.match_trade(self.price + simulate_trade_delta_price, 1, dir)

        self.price += np.int(np.random.normal(self.mu+0.001, self.std))
        self.history.append(self.price)
        if self.on_data:
            self.on_data(self.price, self.symbol)

    def on(self, event, func):
        if event == 'data':
            self.on_data = func
        if event == 'trades':
            self.on_trades = func

'''