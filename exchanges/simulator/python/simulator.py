import __before__
import zmq
import time
import threading
from pymongo import MongoClient
from algo.data_source import *
from algo.root import *
from algo.nanit import *
from algo.dom import *
from algo.virtual_exchange import *
from tqdm import tqdm
import json

shared_context = zmq.Context()


def process_order(order):
    _type = order['name']
    #print("type: ", _type)
    if _type == "new_order":
        action = NewOrder(None, order['dir'])
        action.symbol = order['symbol']
        action.ext_id = order['ext_id']
        action.price = order['price']
        action.amount = order['amount']
        return action
    if _type == "cancel_order":
        action = CancelOrder(None)
        action.order_id = order['order_id']
        action.symbol = order['symbol']
        return action

# listen test_trades


def orders_stream():
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://exchange")
    url = "mongodb://localhost:27000"
    client = MongoClient(url, socketKeepAlive=True)
    pipeline = [
        {"$match": {"operationType": "insert"}},
        {"$project": {"fullDocument._id": 0}}
    ]
    options = {}
    db = client.test
    with db.test_trades.watch(pipeline, **options) as stream:
        for change in stream:
            order = process_order(change['fullDocument'])
            sender.send_pyobj(order)
            #sender.send_json({'trades': change['fullDocument']})


def irq_timer():
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://exchange")
    tick = 0
    while True:
        time.sleep(0.01)
        tick += 1
        sender.send_pyobj(TimeEvent(tick))


def get_reply_sender():
    url = "mongodb://localhost:27000"
    client = MongoClient(url, socketKeepAlive=True)
    db = client.test

    def send(reply):
        db.test_reply.insert_one(reply.__dict__)
    return send


def get_data_sender():
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://127.0.0.1:5671")

    def publish(data):
        publisher.send_json(json.dumps(data.__dict__))

    return publish


def simulator_loop():
    exchange = Exchange()
    si = Market(65000, symbol="Si-3.19")
    exchange.add_market(si)
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://exchange")
    receiver.subscribe(b'')
    send_data = get_data_sender()
    send_reply = get_reply_sender()

    def on_data(price, symbol):
        #print(symbol, price)
        data = DataEvent(symbol, price)
        send_data(data)

    def on_trades(trade):
        print(trade)
        send_reply(trade)
        # print(json.dumps(trade.__dict__))

    exchange.on('data', on_data)
    exchange.on('trades', on_trades)

    while True:
        #msg = receiver.recv_json()
        event = receiver.recv_pyobj()
        if isinstance(event, TimeEvent):
            exchange.step()
        else:
            exchange.apply_raw_order(event)
            print(event)
            #send({'type': 'new_reply', 'code': 0, 'ext_id': 41})


def run():
    orders = threading.Thread(target=orders_stream)
    irq = threading.Thread(target=irq_timer)
    orders.daemon = True
    irq.daemon = True
    orders.start()
    irq.start()
    simulator_loop()


run()
