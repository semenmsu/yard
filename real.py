import zmq
import threading
import time
from pymongo import MongoClient
from algo.data_source import *
from algo.root import *
from algo.nanit import *
from algo.dom import *
#from util import *
import json

shared_context = zmq.Context()


def to_robo(func):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    def pipe_to_robo():
        for channel, event in func():

            if channel == "data_stream":
                event = json.loads(event)
                price = (float(event['bid'])+float(event['ask']))/2
                data = DataEvent(event['symbol'], int(price))
                sender.send_pyobj(data)
            elif channel == "trades_stream":
                _type = event['name']

                reply = None
                if _type == "new_reply":
                    reply = NewReplyEvent(event['code'], event['order_id'])
                    reply.ext_id = event['ext_id']
                elif _type == "cancel_reply":
                    reply = CancelReplyEvent(event['code'], event['amount'])
                    reply.order_id = event['order_id']
                elif _type == "trade_reply":
                    reply = TradeReplyEvent(
                        event['amount'], event['deal_price'])
                    reply.order_id = event['order_id']
                sender.send_pyobj(reply)

            # sender.send_json(event)
    return pipe_to_robo


@to_robo
def data_stream():
    while True:
        try:
            context = zmq.Context()
            receiver = context.socket(zmq.SUB)
            receiver.connect("tcp://127.0.0.1:5561")
            receiver.subscribe(b'Si-3.19')
            while True:
                msg = receiver.recv_multipart()
                body = json.loads(msg[1].decode("ascii"))
                yield "data_stream", msg[1].decode("ascii")
        except Exception as err:
            print("Exception: ", err)
        finally:
            del context
            del receiver
        print("[data stream] wait time for reconnecting")
        time.sleep(5)


@to_robo
def trades_stream():
    url = "mongodb://localhost:27000"
    pipeline = [
        {"$match": {"operationType": "insert"}},
        {"$project": {"fullDocument._id": 0}}
    ]
    options = {}
    while True:
        try:
            client = MongoClient(url, socketKeepAlive=True)
            db = client.test
            with db.trades.watch(pipeline, **options) as stream:
                for change in stream:
                    yield "trades_stream", change['fullDocument']
        except Exception as err:
            print("Exception: ", err)
        finally:
            client.close()
        print("[trades stream] wait 5 sec for reconnecting")
        time.sleep(5)


def get_orders_publisher():
    url = "mongodb://localhost:27000"
    client = MongoClient(url, socketKeepAlive=True)
    db = client.test

    def send(orders):
        for order in orders:
            print(order)

            print(json.dumps(order.__dict__))
            db.orders.insert_one(order.__dict__)
    return send


def create_robo():
    store = DataSource()
    root = Root(store=store)
    robo = Nanit(symbol="Si-3.19", parent=root)

    def on_new_trade(trade):
        print(trade)

    root.on('trade', on_new_trade)
    return root


def robo_loop():
    root = create_robo()

    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')
    actions = []
    publish = get_orders_publisher()
    while True:
        # event = receiver.recv_json()
        event = receiver.recv_pyobj()
        print(event)
        for action in root.do(event):
            actions.append(action)
        publish(actions)
        actions = []


def run():
    data = threading.Thread(target=data_stream)
    trades = threading.Thread(target=trades_stream)
    data.daemon = True
    trades.daemon = True
    data.start()
    trades.start()
    robo_loop()


run()
