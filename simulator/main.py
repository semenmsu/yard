import all_dirs
from pymongo import MongoClient
from algo.order import *
from algo.nanit import *
from algo.root import *
from algo.events import *
from algo.virtual_exchange import *
from collections import deque
import matplotlib.pyplot as plt
from tqdm import tqdm
import statistics

import json


instruments = {}
exchange_cache = {}


def find_instrument(exchange, symbol):
    if exchange in exchange_cache:
        pass
    else:
        if exchange == "moex":
            # url = "mongodb://127.0.0.1:27000"
            url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
            client = MongoClient(url, unicode_decode_error_handler='ignore')
            db = client['test']
            coll = db['sessions']
            cursor = coll.find().sort([("_id", -1)]).limit(1)
            if cursor:
                element = cursor[0]
                fut_instruments = element['fut_instruments']
                fi = {}
                for key, value in fut_instruments.items():
                    min_step = int(value['min_step']['intpart']) / \
                        10**int(value['min_step']['scale'])
                    step_price = int(value['step_price']['intpart']) / \
                        10**int(value['step_price']['scale'])
                    fi[value['isin']] = {
                        "price_mult": 1000000,
                        "amount_mult": 1000000,
                        "min_step_i": int(min_step*1000000),
                        "isin_id": key, "min_step": min_step, "step_price": step_price,
                        "roundto": int(value["roundto"]), "lot_volume": int(value['lot_volume'])}
                exchange_cache[exchange] = fi

                # exchange_cache[exchange] = fut_instruments

    # fut_instruments = exchange_cache[exchange]
    # find
    ex = exchange_cache[exchange]


def find_instrument_and_subscribe(root, exchange_symbol):
    print(exchange_symbol)
    [exchange, symbol] = exchange_symbol.split('@')
    print(exchange, symbol)
    find_instrument(exchange, symbol)
    if symbol in exchange_cache[exchange]:
        config = exchange_cache[exchange][symbol]
        config['symbol'] = exchange_symbol
        print("config", config)
        root.add_symbol_config(config)
    else:
        print("can't find ", exchange_symbol)


def create_robo_from_config(robo_config):
    if robo_config['type'] == "Nanit":
        print("create NANIT")
        [exchange, symbol] = robo_config['symbol'].split('@')
        robo_config['ex_symbol'] = symbol
        robo_config['exchange'] = exchange
        return Nanit2(robo_config)
    return None


def handle_control(root, control):
    if control.command() == "add_robot":
        # robo = TestRobo(control.message["name"])
        config = control.message['config']
        config['type'] = control.message['type']
        config['name'] = control.message['name']
        robo = create_robo_from_config(config)
        if robo:
            root.add(robo)
    elif control.command() == "start" or control.command() == "stop":
        root.control(control)
    elif control.command() == "params":
        root.control(control)


class OrderRouterSim:

    def __init__(self, exchange):
        self.exchange = exchange
        self.orders = []

    def add_order(self, order):
        # hack
        order.symbol = "moex@"+order.symbol
        self.orders.append(order)

    def process_orders(self):
        for order in self.orders:
            self.exchange.apply_raw_order(order)
        self.orders = []


# запускается сам цикл симуляции
def run_exchange_simulation_stream(root, num_cycles=10000, show_profit=False):
    si = Market2(65000, symbol="moex@Si-9.19", mult=1000000)
    exchange = Exchange()
    exchange.add_market(si)

    start_event = ControlMessage.from_json({'message': {
        'to': 'robo', 'name': 'mm-si', 'machine': 'ubuntu', 'runner': 'robo', 'command': 'start'}})

    order_router = OrderRouterSim(exchange)
    profit_series = []
    for i in range(num_cycles):

        if i == 10:
            handle_control(root, start_event)

        if i % 500 == 0:
            strategies = root.show()
            for i in range(len(strategies)):
                if len(profit_series) < i+1:
                    profit_series.append([])
                profit_series[i].append(strategies[i]["profit"]/1000000)

        for event in exchange.step2():
            for order in root.do(event):
                order_router.add_order(order)

        order_router.process_orders()

    # if show_profit:
    #    for profit in profit_series:
    #        plt.plot(profit)
    #    plt.show()
    return profit_series[0]


def run_simulation(shift=5):
    root = Root2("ubuntu", "robo")
    robo_config = {"name": "mm-si", "type": "Nanit", "symbol": "moex@Si-9.19", "buy_limit": "1", "buy_by": "1",
                   "sell_limit": "-1", "sell_by": 1, "buy_shift": shift, "sell_shift": shift}
    robo = create_robo_from_config(robo_config)
    root.add(robo)

    for symbol in root.get_symbols():
        find_instrument_and_subscribe(root, symbol)

    profit = run_exchange_simulation_stream(root, 30000, show_profit=True)
    return profit


def run_simulation_many_times(num_simulations=10, shift=5):

    profits = []
    last_profit = []
    for i in range(num_simulations):
        profit = run_simulation(shift)
        profits.append(profit)
        last_profit.append(profit[-1])

    # print('last_profit', last_profit)
    # print("mean ", statistics.mean(last_profit))
    # input()
    #print(statistics.mean(last_profit))
    #for profit in profits:
    #    plt.plot(profit)
    #
    #plt.show()

    return statistics.mean(last_profit)


def run_multiple_params_simulation(num_simulations=10):
    av_profit = []
    for i in tqdm(range(1, 4)):
        av_profit.append((i, run_simulation_many_times(num_simulations, i)))

    for profit in av_profit:
        print(profit)


# run_simulation()
# run_simulation_many_times()
run_multiple_params_simulation(num_simulations=10)
