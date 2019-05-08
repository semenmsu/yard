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

MACHINE = "ubuntu"
RUNNER = "robo"

shared_context = zmq.Context()


def to_robo(func):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    def pipe_to_robo():
        for channel, event in func():
            #print(channel, event)
            if channel == 'control':
                control = ControlMessage(event)
                sender.send_pyobj(control)
            elif channel == 'timer':
                sender.send_pyobj(event)
            else:
                pass
    return pipe_to_robo


@to_robo
def timer_stream():
    while True:
        time.sleep(5)
        yield "timer", time.time()


@to_robo
def control_stream():
    print("run control stream")
    url = "mongodb://127.0.0.1:27000"
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
    url = "mongodb://127.0.0.1:27000"
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
        print("dump", j)
        sender.send(bytes(j, 'ascii'))

    return publisher


'''
def get_orders_publisher():
    url = "mongodb://127.0.0.1:27000"
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
'''


class TestRoot:
    def __init__(self, machine, runner_name):
        self.machine = machine
        self.name = runner_name
        self.childs = []
        self.store = DataSource()
        pass

    def add(self, child):
        child.add_to_parent(self)
        self.childs.append(child)

    def get_snapshot(self):
        d = dict()
        d['machine'] = self.machine
        d['runner'] = self.name
        strategies = []
        for child in self.childs:
            strategies.append(child.get_snapshot())
        d['strategies'] = strategies
        return d

    def get_config(self):
        d = dict()
        d['machine'] = self.machine
        d['runner'] = self.name
        strategies = []
        for child in self.childs:
            print("config for child", child.name)
            print(child.get_config())
            strategies.append(child.get_config())
        d['strategies'] = strategies
        return d


class TestRobo:
    def __init__(self, name):
        self.name = name
        self.type = "Spreader"
        self.status = "STOPPED"

    def add_to_parent(self, parent):
        pass

    def get_snapshot(self):
        d = dict()
        d['name'] = self.name
        d['profit'] = "1003.2"
        d['position'] = "0"
        d['status'] = self.status
        return d

    def get_config(self):
        d = dict()
        d['name'] = self.name
        d['type'] = self.type
        return d


class ControlMessage:
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return str(self.message)

    def command(self):
        return self.message['command']


def handle_control(root, control):
    if control.command() == "add_robot":
        #robo = TestRobo(control.message["name"])
        config = control.message['config']
        config['type'] = control.message['type']
        config['name'] = control.message['name']
        robo = create_robo_from_config(config)
        if robo:
            root.add(robo)
    elif control.command() == "save":
        save_robo_config(root)


def create_robo_from_config(robo_config):
    if robo_config['type'] == "Spreader":
        print("create spreader robot")
        name = robo_config['name']
        return TestRobo(name)
    elif robo_config['type'] == "Nanit":
        print("create NANIT")
        return Nanit2(robo_config)
    return None


def load_config(root):
    url = "mongodb://127.0.0.1:27000"
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


def robo_loop():
    root = TestRoot("ubuntu", "robo")
    #robo = TestRobo("spreader")
    # root.add(robo)
    load_config(root)
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')
    publish_snapshot = get_snapshot_publisher()
    while True:
        # event = receiver.recv_json()
        event = receiver.recv_pyobj()
        if isinstance(event, ControlMessage):
            handle_control(root, event)
        print(event)
        snapshot = root.get_snapshot()
        publish_snapshot(snapshot)


def run():

    control = threading.Thread(target=control_stream)
    timer = threading.Thread(target=timer_stream)
    control.daemon = True
    timer.daemon = True
    control.start()
    timer.start()
    robo_loop()


run()
