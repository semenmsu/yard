'''
генерация симуляции из файла
необходимо указать:
    - дата yyyymmdd
    - биржа + инструмент moex_fx@USD000UTSTOM, moex_forts@Si-9.19
    - simulator_config


'''
import all_dirs
from forts_config import config
from algo.virtual_exchange import *
from algo.events import *
from algo.order import *
from algo.nanit import *
from algo.root import *
import time
from datetime import datetime
from collections import deque
from heapq import heappush, heappop
import copy
from symbol_finder import SymbolFinder
from sortedcontainers import SortedSet

from readers.moex_fx import *
from readers.utils import *

symbol_finder = SymbolFinder()


# reader = FxTradesReaderCSV(
#   "/home/soarix/data/it-dumps/trades/20190719/fx.trades")
# with FxTradesReaderCSV("/home/soarix/data/it-dumps/trades/20190719/fx.trades", "USD000UTSTOM") as reader:
#    for trade in reader:
#        print(trade)


class Market2:
    def __init__(self, initial_price=0, symbol=None, mult=1000000):
        # self.quote_generator
        self.buy_orders = SortedSet(key=lambda x: (x.price, -x.order_id))  # -1
        self.sell_orders = SortedSet(key=lambda x: (x.price, x.order_id))  # 0
        self.orders = dict()
        self.trades = deque()
        self.price = initial_price
        self.std = 4.0
        self.mu = 0.5
        self.trade_std = 6.0
        self.history = []
        self.trade_p = np.random.binomial(1, 0.2, 1000)
        self.on_data = None
        self.on_trades = None
        self.current_order_id = 1000
        self.symbol = symbol
        self.mult = 1000000
        self.GQ = deque()  # global queue

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
        #print("apply_raw_order ", order)
        # input()

        if isinstance(order, NewOrder):
            self.add(order)
            reply = NewReplyEvent(0, order.order_id)
            reply.ext_id = order.ext_id
            self.GQ.append(reply)

        elif isinstance(order, CancelOrder):
            amount = self.remove(order.order_id)
            if amount > 0:
                reply = CancelReplyEvent(0, amount)
                reply.order_id = order.order_id
                self.GQ.append(reply)
            else:
                reply = CancelReplyEvent(14, 0)
                reply.order_id = order.order_id
                self.GQ.append(reply)

        pass

    def match_trade(self, price, amount, dir):
        if dir == 1:  # check sell
            while len(self.sell_orders) > 0 and self.sell_orders[0].price <= price and amount > 0:
                if self.sell_orders[0].amount >= amount:
                    self.sell_orders[0].amount -= amount
                    # print("new buy trade amount = ", amount,
                    #      "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)

                    # self.on_trades(trade)
                    trade.deal_price *= self.mult
                    self.GQ.append(trade)

                    amount = 0
                    if self.sell_orders[0].amount == 0:
                        self.remove(self.sell_orders[0].order_id)
                else:
                    # print("new buy trade amount = ",
                    #      self.sell_orders[0].amount, "price=", self.sell_orders[0].price)
                    trade = TradeReplyEvent(
                        self.sell_orders[0].amount, self.sell_orders[0].price)
                    trade.order_id = self.sell_orders[0].order_id
                    self.trades.append(trade)
                    # self.on_trades(trade)

                    trade.deal_price *= self.mult
                    self.GQ.append(trade)

                    amount -= self.sell_orders[0].amount
                    self.remove(self.sell_orders[0].order_id)

        else:
            while len(self.buy_orders) > 0 and self.buy_orders[-1].price >= price and amount > 0:
                if self.buy_orders[-1].amount >= amount:
                    self.buy_orders[-1].amount -= amount
                    # print("new sell trade amount = ", amount,
                    #      "price=", self.buy_orders[-1].price)

                    trade = TradeReplyEvent(
                        amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    # self.on_trades(trade)

                    trade.deal_price *= self.mult
                    self.GQ.append(trade)

                    amount = 0
                    if self.buy_orders[-1].amount == 0:
                        self.remove(self.buy_orders[-1].order_id)
                else:
                    # print("new sell trade amount = ",
                    #      self.buy_orders[-1].amount, "price=", self.buy_orders[-1].price)
                    trade = TradeReplyEvent(
                        self.buy_orders[-1].amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    self.trades.append(trade)
                    # self.on_trades(trade)

                    trade.deal_price *= self.mult
                    self.GQ.append(trade)
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
            # print(trade)

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
        self.GQ.append(DataEvent(self.symbol, self.price*self.mult))
        # if self.on_data:
        #
        #    self.on_data(self.price, self.symbol)

    def on(self, event, func):
        if event == 'data':
            self.on_data = func
        if event == 'trades':
            self.on_trades = func


class BidAsk:
    def __init__(self, values):
        self.symbol = values[1]
        self.dir = 1 if values[2] == "bid" else 2
        self.action = values[3]
        self.ts = int(values[4])
        self.price = int(values[7])
        self.amount = int(values[8])
        self.type = "bidask"

    def __repr__(self):
        return f"{self.symbol} dir={self.dir} action={self.action} price={self.price}"

# csv stats (bid, ask)
# csv trades


# data_source {trades, stats, orderbook, ....}
# exchange {moex_fx, moex_forts, moex_eq, }
# data_type {csv, binary, sqlite, ...}
data_reader_dict = {
    "moex_fx": {
        "stats": {
            "csv": {
                "path": lambda date: f"/home/soarix/data/it-dumps/stats/{date}/fx_stat.stats",
                "reader": lambda path, symbol: MoexFxStatsReaderCSV(path, symbol)
            }
        },
        "trades": {
            "csv": {
                "path": lambda date: f"/home/soarix/data/it-dumps/trades/{date}/fx.trades",
                "reader": lambda path, symbol: MoexFxTradesReaderCSV(path, symbol)
            }
        }
    }
}


def GetDataReader(exchange, data_source, data_type):
    path_resolver = data_reader_dict[exchange][data_source][data_type]["path"]
    reader = data_reader_dict[exchange][data_source][data_type]["reader"]
    return lambda date, symbol: reader(path_resolver(date), symbol)


class MarketFromFile:
    def __init__(self, symbol):
        # load data
        # 58317,CNYRUB_TOM,bid,1,1563519904170436000,1563519904170711000,1563519904097891000,9137000,1000000000
        exchange_, symbol_ = symbol.split('@')
        self.symbol = symbol
        self.bidask = []
        self.trades = []
        self.stats = []

        #trades_reader = GetDataReader("moex_fx", "trades", "csv")
        #stats_reader = GetDataReader("moex_fx", "stats", "csv")
        trades_reader = GetDataReader(exchange_, "trades", "csv")
        stats_reader = GetDataReader(exchange_, "stats", "csv")

        # with FxTradesReaderCSV("/home/soarix/data/it-dumps/trades/20190719/fx.trades", "USD000UTSTOM") as reader:
        #    for trade in reader:
        #        self.trades.append(trade)
        with trades_reader("20190719", symbol_) as tr:
            for trade in tr:
                self.trades.append(trade)

        with stats_reader("20190719", symbol_) as sr:
            for stat in sr:
                self.stats.append(stat)

        self.trade_index = 0
        self.trade_len = len(self.trades)-1

        #self.bidask = merge_by_ts(self.stats,self.trades)



        with open("/home/soarix/data/it-dumps/stats/20190719/fx_stat.stats") as f:
            for line in f:
                values = line.split(',')
                if (values[1] == symbol_):
                    ba = BidAsk(values)
                    while self.trade_index < self.trade_len:
                        if self.trades[self.trade_index].ts < ba.ts:
                            self.bidask.append(self.trades[self.trade_index])
                            self.trade_index += 1
                        else:
                            break
                    self.bidask.append(ba)
        

        self.len = len(self.bidask)-1

        self.index = 0
        self.bidask_index = 0

        self.channel = None
        self.trades_channel = None
        self.bid = 0
        self.ask = 0
        self.buy_orders = SortedSet(key=lambda x: (x.price, -x.order_id))  # -1
        self.sell_orders = SortedSet(key=lambda x: (x.price, x.order_id))  # 0
        self.orders = dict()
        self.current_order_id = 1

    def add(self, order):
        self.orders[order.order_id] = order
        if order.dir == 1:
            self.buy_orders.add(order)
        else:
            self.sell_orders.add(order)

    def get_buy_index(self, price, order_id):
        order_id = -order_id
        index = self.buy_orders.bisect_key_left((price, order_id))
        if index == len(self.buy_orders):
            return -1
        order = self.buy_orders[index]
        if price == order.price and -order_id == order.order_id:
            return index
        return -1

    def get_sell_index(self, price, order_id):
        index = self.sell_orders.bisect_key_left((price, order_id))
        if index == len(self.sell_orders):
            return -1
        order = self.sell_orders[index]
        if price == order.price and order_id == order.order_id:
            return index
        return -1

    def remove(self, order_id):
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.dir == 1:
                idx = self.get_buy_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find buy_order with order_id {order_id}")
                amount = self.buy_orders[idx].amount
                del self.buy_orders[idx]
                del self.orders[order_id]
                return amount
            else:
                idx = self.get_sell_index(order.price, order.order_id)
                if idx == -1:
                    raise Exception(
                        f"can't find sell_order with order_id {order_id}")
                amount = self.sell_orders[idx].amount
                del self.sell_orders[idx]
                del self.orders[order_id]
                return amount

        return -1

    def apply_raw_order(self, order, pq):
        # print(order)

        if isinstance(order, NewOrder):
            #print("real_price", order.price)
            # input()
            self.add(order)
            reply = NewReplyEvent(0, order.order_id)
            reply.ext_id = order.ext_id
            reply.ts = order.ts
            self.channel.write(reply, pq)
            # self.GQ.append(reply)

        elif isinstance(order, CancelOrder):
            amount = self.remove(order.order_id)
            if amount > 0:
                reply = CancelReplyEvent(0, amount)
                reply.order_id = order.order_id
                reply.ts = order.ts
                self.channel.write(reply, pq)
                # self.GQ.append(reply)
            else:
                reply = CancelReplyEvent(14, 0)
                reply.order_id = order.order_id
                reply.ts = order.ts
                self.channel.write(reply, pq)
                # self.GQ.append(reply)
        # input()

    def match_trade(self, trade, pq, ts):
        price = trade.price
        amount = trade.amount
        dir = trade.dir
        #print("bid/ask", self.bid, self.ask)
        #print("try match ", trade)
        # input()

        if dir == 1:  # check sell
            while len(self.sell_orders) > 0 and self.sell_orders[0].price <= price and amount > 0:
                if self.sell_orders[0].amount >= amount:
                    self.sell_orders[0].amount -= amount
                    # print("new buy trade amount = ", amount,
                    #      "price=", self.sell_orders[0].price)
                    trade_reply = TradeReplyEvent(
                        amount, self.sell_orders[0].price)
                    trade_reply.order_id = self.sell_orders[0].order_id
                    trade_reply.ts = ts
                    trade_reply.dir = 2
                    trade_reply.symbol = self.symbol
                    # self.trades.append(trade)

                    # self.on_trades(trade)
                    #trade.deal_price *= self.mult
                    # self.GQ.append(trade)
                    #print("[SELL] trade.deal_price = ", trade_reply.deal_price)
                    self.trades_channel.write(trade_reply, pq)

                    amount = 0
                    if self.sell_orders[0].amount == 0:
                        self.remove(self.sell_orders[0].order_id)
                    # input()
                else:
                    # print("new buy trade amount = ",
                    #      self.sell_orders[0].amount, "price=", self.sell_orders[0].price)
                    trade_reply = TradeReplyEvent(
                        self.sell_orders[0].amount, self.sell_orders[0].price)
                    trade_reply.order_id = self.sell_orders[0].order_id
                    trade_reply.ts = ts
                    trade_reply.dir = 2
                    trade_reply.symbol = self.symbol
                    # self.trades.append(trade)
                    # self.on_trades(trade)

                    #trade.deal_price *= self.mult
                    # self.GQ.append(trade)
                    #print("[SELL] trade.deal_price = ", trade_reply.deal_price)
                    self.trades_channel.write(trade_reply, pq)

                    amount -= self.sell_orders[0].amount
                    self.remove(self.sell_orders[0].order_id)
                    # input()

        else:
            while len(self.buy_orders) > 0 and self.buy_orders[-1].price >= price and amount > 0:
                if self.buy_orders[-1].amount >= amount:
                    self.buy_orders[-1].amount -= amount
                    print("new sell trade amount = ", amount,
                          "price=", self.buy_orders[-1].price)

                    trade_reply = TradeReplyEvent(
                        amount, self.buy_orders[-1].price)
                    trade.order_id = self.buy_orders[-1].order_id
                    trade_reply.ts = ts
                    trade_reply.dir = 1
                    trade_reply.symbol = self.symbol
                    # self.trades.append(trade)
                    # self.on_trades(trade)

                    #trade.deal_price *= self.mult
                    # self.GQ.append(trade)
                    self.trades_channel.write()
                    #print("[BUY] trade.deal_price = ", trade_reply.deal_price)
                    self.trades_channel.write(trade_reply, pq)

                    amount = 0
                    if self.buy_orders[-1].amount == 0:
                        self.remove(self.buy_orders[-1].order_id)
                    # input()
                else:
                    # print("new sell trade amount = ",
                    #      self.buy_orders[-1].amount, "price=", self.buy_orders[-1].price)
                    trade_reply = TradeReplyEvent(
                        self.buy_orders[-1].amount, self.buy_orders[-1].price)
                    trade_reply.order_id = self.buy_orders[-1].order_id
                    trade_reply.ts = ts
                    trade_reply.dir = 1
                    trade_reply.symbol = self.symbol
                    # self.trades.append(trade)
                    # self.on_trades(trade)

                    #trade.deal_price *= self.mult
                    #print("[BUY] trade.deal_price = ", trade_reply.deal_price)
                    self.trades_channel.write(trade_reply, pq)
                    # self.GQ.append(trade)
                    amount -= self.buy_orders[-1].amount
                    self.remove(self.buy_orders[-1].order_id)
                    # input()

    def set_channel(self, name, channel):
        if name == "data":
            self.channel = channel
        elif name == "trades":
            self.trades_channel = channel
        else:
            raise Exception(f"set unknow channel {name} for market")

    def update_bid_ask(self, event):
        if event.dir == 1:
            if event.action == "1":
                self.bid = event.price
        elif event.dir == 2:
            if event.action == "1":
                self.ask = event.price
        else:
            raise Exception("dir != {1,2}")

    def get_price(self):
        return int((float(self.bid + self.ask)/(2*1000_000))*1000_000)

    def recv(self, event, pq):
        # print(self.idx, "market recv event ",
        #      get_datetime_str_from_unix_time_ns(event.ts))
        if isinstance(event, NewOrder):
            self.current_order_id += 1
            event.order_id = self.current_order_id

        self.apply_raw_order(event, pq)

    # возвращает источник и событие

    def next2(self, ts, prev_event):
        while self.index < self.len and self.bidask[self.index].ts <= ts:
            self.index += 1
        if self.index < self.len:
            yield (self, self.bidask[self.index])
        else:
            return None

    def next(self, pq, ts):
        while self.index < self.len and self.bidask[self.index].ts <= ts:
            # if self.channel:  # apply event
            if self.bidask[self.index].type == "bidask":
                self.update_bid_ask(self.bidask[self.index])
                data_event = DataEvent(self.symbol, self.get_price())
                data_event.ts = self.bidask[self.index].ts
                self.channel.write(data_event, pq)
            elif self.bidask[self.index].type == "trade":
                self.match_trade(self.bidask[self.index], pq, ts)

            self.index += 1
        if self.index < self.len:
            event = self.bidask[self.index]
            heappush(pq, (event.ts, self.idx))
        else:
            return None


class Exchange2:
    def __init__(self):
        self.markets = dict()
        self.on_data = None
        self.on_trades = None
        self.current_order_id = 1000

    def add_market(self, market):
        self.markets[market.symbol] = market

    def apply_raw_order(self, order):
        if isinstance(order, NewOrder):
            self.current_order_id += 1
            order.order_id = self.current_order_id
        self.markets[order.symbol].apply_raw_order(order)

    def step(self, ts):
        # обновляем данные
        for symbol, market in self.markets.items():
            market.step(ts)

        # считываем генерируемые события
        for symbol, market in self.markets.items():
            while len(market.GQ):
                event = market.GQ.popleft()
                yield event


class TimerNS:
    def __init__(self, period_in_ns):
        self.period_in_ns = period_in_ns


def CreateRoboFromConfig(robo_config):
    if robo_config['type'] == "Nanit":
        print("create NANIT")
        [exchange, symbol] = robo_config['symbol'].split('@')
        robo_config['ex_symbol'] = symbol
        robo_config['exchange'] = exchange
        return Nanit2(robo_config)
    return None


def get_datetime_str_from_unix_time_ns(unix_ts):
    timestamp = datetime.fromtimestamp(unix_ts/1000_000_000)
    #print("time_stamp", timestamp)
    ns = unix_ts % 1000_000_000
    mks = int(ns/1000)
    datetime_str = timestamp.strftime(
        '%Y-%m-%d %H:%M:%S') + "."+str(mks).zfill(6)
    return datetime_str


# внутри себя имеет каналы на биржи
class OrderRouter:

    def __init__(self):
        self.orders = []
        self.channels = dict()

    def add_order(self, order):
        # hack
        #order.symbol = "moex@"+order.symbol
        self.orders.append(order)

    # распределяет ордера по symbol
    def add_channel(self, symbol, channel):
        self.channels[symbol] = channel

    def process_orders(self, ts, pq):
        for order in self.orders:
            # self.exchange.apply_raw_order(order)

            order.ts = ts
            self.channels[order.symbol].write(order, pq)

        self.orders = []


class StrategyEngine:
    def __init__(self):
        print("StrategyEngine Constructor")
        self.events = []
        self.root = Root2("ubuntu", "robo")
        robo_config = {"name": "mm-si", "type": "Nanit", "symbol": "moex_fx@USD000UTSTOM", "buy_limit": "1", "buy_by": "1",
                       "sell_limit": "-1", "sell_by": 1, "buy_shift": 4, "sell_shift": 4}
        robo = CreateRoboFromConfig(robo_config)
        self.root.add(robo)
        for symbol in self.root.get_symbols():
            conf = symbol_finder.subscribe(self.root, symbol)
        self.order_router = OrderRouter()
        self.Q = deque()
        self.all_trades = []

    def recv(self, event, pq):
        #print(self.idx, "recv job ", get_datetime_str_from_unix_time_ns(event.ts))
        # print(event)
        if isinstance(event, TradeReplyEvent):
            self.all_trades.append(event)
            # input()

        for order in self.root.do(event):
            # hack
            if isinstance(order, NewOrder):
                order.price *= 1000000
                order.price = int(order.price)
                # print(order)
                #print("price from strategy = ", order.price)
                # print(self.root.show())
            self.order_router.add_order(order)

        # у всех событий должно быть обязательно
        self.order_router.process_orders(event.ts, pq)

        # print(self.root.show())

        # input()

    def push(self, event):
        self.Q.append(event)

    def next(self, pq, ts):
        while len(self.Q) and self.Q[0].ts <= ts:
            event = self.Q.popleft()
            # self.recv(event)
            # мне не нравится, нужно будет переделать
            self.root.control(event)
            print("[STRATEGY_ENGINE]", event)
            # input()

        if len(self.Q):
            heappush(pq, (self.Q[0].ts, self.idx))


# подает в end_point данные с некоторой задержкой
# в pq добавляет source
class StochasticChannel:
    def __init__(self, end_point):
        self.end_point = end_point
        self.Q = deque()

    def get_stochastic_value_from_ts_ns(self, ts):
        return ts + 10_000_000  # добавили 10мc

    def write(self, event, pq):  # аналогия с сокет write
        if len(self.Q):
            head = self.Q[0]
            tail = self.Q[-1]
            ts = self.get_stochastic_value_from_ts_ns(event.ts)
            if ts <= tail.ts:
                event.ts = tail.ts
            else:
                event.ts = ts
        else:
            ts = self.get_stochastic_value_from_ts_ns(event.ts)
            event.ts = ts
        self.Q.append(event)
        #heappush(pq, (event.ts, self))
        heappush(pq, (event.ts, self.idx))

    def next(self, pq, ts):
        while len(self.Q) and self.Q[0].ts <= ts:
            event = self.Q.popleft()
            self.end_point.recv(event, pq)
        return None


# heapq (ts, obj) если совпадает ts, то видимо сравнивает obj
class Register:
    def __init__(self):
        self.index = 0
        self.objects = []

    def register(self, obj):
        self.objects.append(obj)
        obj.idx = self.index
        self.index += 1

    def get_object_by_id(self, id):
        return self.objects[id]


def strategy_pprint(snapshot):
    for snap in snapshot:
        profit = float(snap["profit"])
        total_trades = int(snap["total_trades"])
        profit_per_volume = 0
        if total_trades:
            profit_per_volume = profit/total_trades
        print(
            f"profit={profit} total_trades={total_trades} profit_per_volume={profit_per_volume}")


def run():

    # print(config)
    #print("start_time ", start_time)
    # datetime_str = config.get_datetime_str_from_unix_time_ns(
    #    start_time)
    #print("start_time_str ", datetime_str)
    register = Register()
    pq = []
    #start_time = config.get_unix_time_ns("10:05:00")
    #heappush(pq, (start_time, None))
    market = MarketFromFile("moex_fx@USD000UTSTOM")
    register.register(market)
    market.next(pq, 0)  # размещаем в pq

    startegy_engine = StrategyEngine()
    register.register(startegy_engine)
    for control_message in config.control_messages:
        print(control_message)
        cntl_json = {'message': control_message['body']}
        control_event = ControlMessage.from_json(cntl_json)
        control_event.ts = config.get_unix_time_ns(control_message["ts"])
        # print(control_event)
        startegy_engine.push(control_event)
    startegy_engine.next(pq, 0)

    channel = StochasticChannel(startegy_engine)
    register.register(channel)
    market.set_channel("data", channel)
    trades_channel = StochasticChannel(startegy_engine)
    register.register(trades_channel)
    market.set_channel("trades", trades_channel)

    to_market_channel = StochasticChannel(market)
    register.register(to_market_channel)
    startegy_engine.order_router.add_channel(market.symbol, to_market_channel)

    while len(pq):
        (ts, id_) = heappop(pq)
        # print(get_datetime_str_from_unix_time_ns(ts))
        if id_ != None:
            source = register.get_object_by_id(id_)
            source.next(pq, ts)
            # input()

    # print(startegy_engine.root.show())
    for trade in startegy_engine.all_trades:
        print(
            f"{trade.ts},{get_datetime_str_from_unix_time_ns(trade.ts)},{trade.get_csv()}")
    print(startegy_engine.root.show())
    strategy_pprint(startegy_engine.root.show())

    '''
    while len(pq):
        ts, source_and_event = heappop(pq)

        try:
            event = next(market.next(ts)) # прокручивает 
            if event:
                heappush(pq, (event[1].ts, event))
            print('timestamp', event[1].ts)
            print("next_step")
            input()
        except StopIteration:
            print("stop_iteration")

    #entry_time = get_datetime_str_from_unix_time_ns(next(event).entry_time)
    # print(entry_time)
    '''


run()
