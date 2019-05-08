import zmq
import threading
import time
from pymongo import MongoClient
from algo.data_source import *
from algo.timers import *
from algo.root import *
from algo.nanit import *
from algo.dom import *
#from util import *
import json
import queue
from pprint import pprint

MACHINE = "ubuntu"
RUNNER = "robo"

shared_context = zmq.Context()
subscribe_queue = queue.Queue()
instruments = {}
exchange_cache = {}


def to_robo(func):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    def pipe_to_robo():
        for channel, event in func():

            if channel == "data_stream":
                event = json.loads(event)
                price = (float(event['bid'])+float(event['ask']))/(2)
                data = DataEvent(event['symbol'], int(price))
                sender.send_pyobj(data)
            elif channel == "orders_stream":

                _type = event['type']

                reply = None
                if _type == "new_reply":
                    reply = NewReplyEvent(event['code'], event['order_id'])
                    reply.ext_id = int(event['ext_id'])
                    reply.message = event['message']
                elif _type == "cancel_reply":
                    reply = CancelReplyEvent(event['code'], event['amount'])
                    reply.order_id = int(event['order_id'])
                elif _type == "trade_reply":
                    reply = TradeReplyEvent(
                        event['amount'], event['deal_price'])
                    reply.order_id = int(event['order_id'])
                sender.send_pyobj(reply)
            elif channel == "trades_stream":

                action = int(event['action'])
                if action == 2:
                    intpart = int(event['deal_price']['intpart'])
                    scale = int(event['deal_price']['scale'])
                    deal_price = int(intpart/10**scale)
                    reply = TradeReplyEvent(
                        int(event['amount']), deal_price)
                    reply.order_id = int(event['orderid'])
                    sender.send_pyobj(reply)
                # print(event)
            elif channel == 'control':
                control = ControlMessage(event)
                sender.send_pyobj(control)
            elif channel == 'timer':
                time_event = TimeEvent(event['time'])
                time_event.type = event['type']
                sender.send_pyobj(time_event)

            # sender.send_json(event)
    return pipe_to_robo


@to_robo
def data_stream():
    while True:
        try:
            context = zmq.Context()
            receiver = context.socket(zmq.SUB)
            receiver.connect("tcp://127.0.0.1:5561")
            receiver.setsockopt(zmq.RCVTIMEO, 2000)
            # receiver.subscribe(b'Si-3.19')
            while True:
                # subscirbe
                while not subscribe_queue.empty():
                    item = subscribe_queue.get()
                    if item:
                        print("data_stream subscribre", item)
                        receiver.subscribe(bytes(item, "ascii"))

                try:  # don't like
                    msg = receiver.recv_multipart()
                    yield "data_stream", msg[1].decode("ascii")
                except:
                    pass
        except Exception as err:
            print("Exception: ", err)
        finally:
            del context
            del receiver
        print("[data stream] wait time for reconnecting")
        time.sleep(5)


@to_robo
def orders_stream():
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    pipeline = [
        {"$match": {"operationType": "insert",
                    "fullDocument.from": "cgate-gw", "fullDocument.to": "robo"}},
        {"$project": {"fullDocument._id": 0}}
    ]
    options = {}
    while True:
        try:
            client = MongoClient(url, socketKeepAlive=True)
            db = client.test
            coll = db['test']
            with coll.watch(pipeline, **options) as stream:
                for change in stream:
                    yield "orders_stream", change['fullDocument']
        except Exception as err:
            print("Exception: ", err)
        finally:
            client.close()
        print("[orders stream] wait 5 sec for reconnecting")
        time.sleep(5)


@to_robo
def trades_stream():
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    pipeline = [
        {"$match": {"operationType": "insert",
                    "fullDocument.comment": "robo"}},
        {"$project": {"fullDocument._id": 0}}
    ]
    options = {}
    while True:
        try:
            client = MongoClient(url, socketKeepAlive=True)
            db = client.test
            coll = db['trades']
            print("watch trades stream")
            with coll.watch(pipeline, **options) as stream:
                for change in stream:
                    yield "trades_stream", change['fullDocument']
        except Exception as err:
            print("Exception: ", err)
        finally:
            client.close()
        print("[orders stream] wait 5 sec for reconnecting")
        time.sleep(5)


def get_orders_publisher():
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    client = MongoClient(url, socketKeepAlive=True)
    db = client.test
    coll = db['test']

    def send(orders):
        for order in orders:
            print(order)

            # print(json.dumps(order.__dict__))
            # for real use send_orders
            coll.insert_one(order.toDict("robo", "cgate-gw"))
    return send


class ControlMessage:
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return str(self.message)

    def command(self):
        return self.message['command']


@to_robo
def timer_stream():
    while True:
        time.sleep(5)
        yield "timer", {"type": "5s", "time": time.time()}


@to_robo
def control_stream():
    print("run control stream")
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    pipeline = [
        {"$match": {"operationType": "insert",
                    "fullDocument.to": "robo"}},
        {"$project": {"fullDocument._id": 0}}
    ]
    options = {}
    while True:
        try:
            client = MongoClient(url, socketKeepAlive=True)
            db = client.test
            coll = db['control']
            with coll.watch(pipeline, **options) as stream:
                for change in stream:
                    yield "control", change['fullDocument']
        except Exception as err:
            print("Exception: ", err)
        finally:
            client.close()
        print("[orders stream] wait 5 sec for reconnecting")
        time.sleep(5)

# robots collection


def save_robo_config(root):
    robo_config = root.get_config()
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    client = MongoClient(url)
    db = client.test
    coll = db.robots
    # coll.insert_one(robo_config)
    coll.replace_one({"machine": MACHINE, "runner": RUNNER},
                     robo_config, upsert=True)


def get_snapshot_publisher():
    sender = shared_context.socket(zmq.PUB)
    sender.connect("tcp://127.0.0.1:5562")

    def publisher(data):
        #print("publish", data)
        # bytes(snapshot, 'ascii'))
        j = json.dumps(data)
        #print("dump", j)
        sender.send(bytes(j, 'ascii'))

    return publisher


def find_instrument(exchange, symbol):
    if exchange in exchange_cache:
        pass
    else:
        if exchange == "moex":
            #url = "mongodb://127.0.0.1:27000"
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

                #exchange_cache[exchange] = fut_instruments

    #fut_instruments = exchange_cache[exchange]
    # find
    ex = exchange_cache[exchange]

    #print(symbol, ex[symbol])


def find_instrument_and_subscribe(root, exchange_symbol):
    print(exchange_symbol)
    [exchange, symbol] = exchange_symbol.split('@')
    print(exchange, symbol)
    find_instrument(exchange, symbol)
    if exchange_cache[exchange][symbol]:
        config = exchange_cache[exchange][symbol]
        config['symbol'] = exchange_symbol
        print("config", config)
        root.add_symbol_config(config)
    # subscribe_queue.put(symbol)
    subscribe_queue.put(exchange_symbol)


def handle_control(root, control):
    if control.command() == "add_robot":
        #robo = TestRobo(control.message["name"])
        config = control.message['config']
        config['type'] = control.message['type']
        config['name'] = control.message['name']
        robo = create_robo_from_config(config)
        if robo:
            root.add(robo)
            for symbol in root.get_symbols():
                find_instrument_and_subscribe(root, symbol)
                # subscribe_queue.put(symbol)
    elif control.command() == "save":
        save_robo_config(root)
    elif control.command() == "start" or control.command() == "stop":
        root.control(control)
    elif control.command() == "params":
        root.control(control)


def create_robo_from_config(robo_config):
    if robo_config['type'] == "Nanit":
        print("create NANIT")
        [exchange, symbol] = robo_config['symbol'].split('@')
        robo_config['ex_symbol'] = symbol
        robo_config['exchange'] = exchange
        return Nanit2(robo_config)
    return None


def load_config(root):
    #url = "mongodb://127.0.0.1:27000"
    url = "mongodb://172.26.1.2:27017,172.26.1.3:27018/test?replicaSet=rs0"
    client = MongoClient(url)
    db = client["test"]
    coll = db["robots"]
    config = coll.find_one({"machine": MACHINE, "runner": RUNNER})
    if config:
        strategies = config['strategies']
        for conf in strategies:
            # print(conf)
            robo = create_robo_from_config(conf)
            if robo:
                root.add(robo)

        for symbol in root.get_symbols():
            # subscribe_queue.put(symbol)
            find_instrument_and_subscribe(root, symbol)

        root.print_instruments()


def robo_loop():

    root = Root2("ubuntu", "robo")
    #robo = TestRobo("spreader")
    # root.add(robo)
    load_config(root)
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')
    publish_snapshot = get_snapshot_publisher()
    actions = []
    publish = get_orders_publisher()
    while True:
        # event = receiver.recv_json()
        event = receiver.recv_pyobj()
        if not isinstance(event, DataEvent) and not isinstance(event, TimeEvent):
            print(event)
        if isinstance(event, ControlMessage):
            handle_control(root, event)
            snapshot = root.get_snapshot()
            publish_snapshot(snapshot)
            continue

        if isinstance(event, TimeEvent):
            snapshot = root.get_snapshot()
            publish_snapshot(snapshot)

        for action in root.do(event):
            actions.append(action)
        publish(actions)
        actions = []


def run():
    data = threading.Thread(target=data_stream)
    orders = threading.Thread(target=orders_stream)
    trades = threading.Thread(target=trades_stream)
    control = threading.Thread(target=control_stream)
    timer = threading.Thread(target=timer_stream)
    control.daemon = True
    timer.daemon = True
    data.daemon = True
    orders.daemon = True
    trades.daemon = True
    data.start()
    orders.start()
    trades.start()
    control.start()
    timer.start()
    robo_loop()


run()
