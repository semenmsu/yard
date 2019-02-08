import zmq
import time
import threading
from algo.data_source import *
from algo.root import *
from algo.nanit import *
from algo.dom import *
from algo.virtual_exchange import *
from tqdm import tqdm
import matplotlib.pyplot as plt
from collections import deque
from strategies.arbitrage import Arbitrage

shared_context = zmq.Context()


class TheEnd:
    pass


def exchange_stream():
    q_data = deque()
    q_orders = deque()
    q_trades = deque()
    sender = shared_context.socket(zmq.PAIR)
    sender.connect("inproc://robo")

    #exchange = Exchange(65000, symbol="Si-3.19")
    si = Market(65000, symbol="Si-3.19")
    rts = Market(65000, symbol="RTS-3.19")
    exchange = Exchange()
    exchange.add_market(si)
    exchange.add_market(rts)

    def on_data(price, symbol):
        q_data.append({"price": price, "symbol": symbol})

    def on_trades(trade):
        q_trades.append(trade)

    exchange.on('data', on_data)
    exchange.on('trades', on_trades)

    events = []
    for i in tqdm(range(10000)):
        exchange.step()

        while len(q_data):
            l1 = q_data.popleft()
            event = DataEvent(l1["symbol"], l1["price"])
            events.append(event)

        while len(q_trades):
            trade = q_trades.popleft()
            events.append(trade)

        sender.send_pyobj(events)
        events = []
        actions = sender.recv_pyobj()
        for action in actions:
            exchange.apply_raw_order(action)

    sender.send_pyobj(TheEnd())


def robo_loop():
    store = DataSource()
    root = Root(store=store)
    #robo = Nanit(symbol="Si-3.19", store=store)
    robo = Arbitrage(store=store)
    mount(root, robo)
    add_child(root, robo)

    receiver = shared_context.socket(zmq.PAIR)
    receiver.bind("inproc://robo")

    def on_new_trade(trade):
        robo.profit_history.append(robo.profit())

    root.on('trade', on_new_trade)

    actions = []
    while True:
        events = receiver.recv_pyobj()
        if isinstance(events, TheEnd):
            break
        for event in events:
            for action in root.do(event):
                actions.append(action)
        receiver.send_pyobj(actions)
        actions = []

    plt.plot(robo.profit_history)
    plt.show()


def run():
    exchange_simulator = threading.Thread(target=exchange_stream)
    exchange_simulator.daemon = True
    exchange_simulator.start()
    robo_loop()
    print("close program")


if __name__ == '__main__':
    run()
