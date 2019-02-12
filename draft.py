import zmq
#import time
import threading
#import pymongo
from pymongo import MongoClient
#from bson.json_util import dumps
from bson.json_util import loads
from enum import Enum
import copy


class OrderStatus(Enum):
    FREE = 1
    PENDING_NEW = 2
    NEW = 3
    PENDING_CANCEL = 4
    CANCELED = 5

db_instruments = {}
db_services = {}
isin_to_symbol = {}
robo_name = "robo"

shared_context = zmq.Context()

def process_data_stream(msg):
    values = msg.split(b':')
    payload = loads(values[2].decode('utf-8'))
    symbol = isin_to_symbol[payload[0]]
    data = {'symbol': symbol, 'bid': payload[1], 'ask': payload[2]}
    # sender.send_json({"data": msg.decode('utf-8')})
    return data

def process_trade_stream(msg):
    pass

def process_control_stream(msg):
    pass

def data_stream(symbols=[], config={}):con
    print(config)
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    if 'url' in config:
        url = config['url']
    else:
        url = "tcp://localhost:5561"
    #socket.connect("tcp://localhost:5561")
    socket.connect(url)
    for symbol in symbols:
        if symbol not in db_instruments:
            exit(2)
        print(db_instruments[symbol])
        sub_str = b'common:'+bytes(str(db_instruments[symbol]['isin_id']), 'ascii')
        print(sub_str)
        socket.subscribe(sub_str)
    #socket.subscribe(b'common:' + b'558546')
    while True:
        msg = socket.recv()
        data = process_data_stream(msg)
        sender.send_json({'data': data})


def trade_stream(robo_name, config={}):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    if 'url' in config:
        url = config['url']
    else:
        url = "mongodb://localhost:27000"
    client = MongoClient(url, socketKeepAlive=True)
    pipeline = [
        {"$match": {"operationType": "insert"}},
        {"$project": {"fullDocument._id": 0}}  # important for python conversion to json
    ]
    options = {}
    db = client.test
    with db.trades.watch(pipeline, **options) as stream:
        for change in stream:
            if 'fullDocument' in change:
                sender.send_json({'trade': change['fullDocument']})

def control_stream(robo_name, config={}):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")

    url = "mongodb://localhost:27000"
    client = MongoClient(url, socketKeepAlive=True)
    pipeline = [
        {"$match": {"fullDocument.name": "robo", "operationType": "insert"}},
        {"$project": {"fullDocument._id": 0}} #important for python conversion to json
    ]
    option = {}
    db = client.test
    with db.robo_controls.watch(pipeline, **option) as stream:
        for change in stream:
            if 'fullDocument' in change:
                sender.send_json({"control": change['fullDocument']})


def supervisor():
    pass


def setup():
    url = "mongodb://localhost:27000"
    try:
        client = MongoClient(url, socketKeepAlive=True)
        client.server_info()
    except:
        print(err)
        exit(1)

    db = client.test

    #db_instruments
    futures = db.fut_instruments.find({},{"_id": 0})
    for instument in futures:
        #print(instument)
        db_instruments[instument["isin"]] = instument;
        isin_to_symbol[instument['isin_id']] = instument['isin']

    services = db.services.find()
    for service in services:
        #print(service)
        #del service['_id']
        db_services[service["name"]]=service

    print(db_services)

    return True


def cleanup():
    pass


def robo_loop():
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')
    state ={"print": True}

    while True:
        msg = receiver.recv_json()
        commands=[]
        if state["print"]:
            if 'control' in msg:
                print("[robo] control: ", msg['control'])
                commands = robo.update('control', msg['control'])
            elif 'data' in msg:
                print("[robo] data   : ", msg['data'])
                commands = robo.update('data', msg['data'])
            elif 'trade' in msg:
                print("[robo] trade  : ", msg['trade'])
                commands = robo.update('trade', msg['trade'])

        if len(commands)>0:
            pass


def publisher():
    url = "mongodb://localhost:27000"
    try:
        client = MongoClient(url, socketKeepAlive=True)
        client.server_info()
    except ValueError as err:
        print(err)
        exit(1)

    db = client.test
    send_orders = db.send_orders

    def send(order):
        print("@inside send order")
        send_orders.insert_one(order)

    return send


class BaseRobo:
    def __init__(self, name):
        self.symbols = []
        self.symbol2instrument = {}
        self.initialization()
        self.name = name
        self.trade_state = "stop"
        self.commands = []
        self.pub = publisher()

    def id(self, symbol):
        self.symbols.append(symbol)
        self.symbol2instrument[symbol] ={}

        return self.symbol2instrument[symbol]


BUY = 1
SELL = 2

class OrderState:

    def __init__(self, dir):
        self.ext_id = 0
        self.order_id = 0
        self.price = 0
        self.amount = 0
        self.rest_amount = 0
        self.dir = dir
        self.status = OrderStatus.FREE
        self.sending_time = 0
        self.create_time = 0
        self.last_code = 0


    def free(self):
        self.status = OrderStatus.FREE
        self.order_id = 0
        self.amount = 0
        self.price = 0
        self.rest_amount = 0
        self.sending_time = 0
        self.create_time = 0
        self.last_code = 0

class OrderDesire:
    def __init__(self):
        self.price = 0
        self.amount = 0

class Action:
    def __init__(self, name):
        self.name = name


class NewOrder:
    def __init__(self, isin_id, dir):
        self.user_code = 1
        self.isin_id = isin_id
        self.ext_id = 0
        self.price = 0
        self.amount = 0
        self.dir = dir


class CancelOrder:
    def __init__(self, isin_id):
        self.isin_id = isin_id
        self.user_code = 1
        self.order_id = 0


# The Whole idea  About all system State Machine Replication
# Idea: functional component tries make state(real world) and desire(our goal) close as possible (goal oriented)
# realization: use append_only list
# state1 -> action -> state2 -> action -> state3 -> action -> ....
# conditions ... this is object for external conditions (dependency injection, don't like bit connectivity)
#pyrsistent module
class Long:

    def __init__(self, instrument, restrictions=None):
        self.instrument = instrument
        self.state = OrderState(BUY)
        self.desire = OrderDesire()

        self.session_id = 0
        self.total_money = 0
        self.total_trades = 0
        self.is_settings_loaded = 0
        self.min_step_price = 1
        self.isin_id = 1
        self.change_price_limit = 1  # custom settings
        self.dir = BUY

        if restrictions:
            self.restrictions = restrictions
        else:
            self.restrictions = lambda: False

# utils
    def generate_new_order(self, state):
        order = NewOrder(self.isin_id, self.dir)
        order.price = state.price
        order.amount = state.amount
        return order

    def generate_cancel_order(self, state):
        cancel = CancelOrder(self.isin_id)
        cancel.order_id = state.order_id
        return cancel

    def price_changing_is_big(self):
        if abs(self.desire.price - self.state.price) > self.change_price_limit:
            return True
        return False

    def want_trade(self):
        return self.desire.amount > 0

# state changers:
    def next_state_and_order(self, state, desire, action):
        if action.name == "new":
            next_state = copy.copy(state)
            next_state.status = OrderStatus.PENDING_NEW
            next_state.price = desire.price
            next_state.amount = desire.amount
            next_state.rest_amount = desire.amount
            order = self.generate_new_order(next_state)
            return next_state, order

        elif action.name == "cancel":
            next_state = copy.copy(state)
            next_state.status = OrderStatus.PENDING_CANCEL
            cancel = self.generate_cancel_order(next_state)
            return next_state, cancel

    def write_new_order(self):
        pass

    def write_cancel_order(self):
        pass

    def reply_new(self):
        pass

    def reply_cancel(self):
        pass

    def reply_trade(self):
        pass

# generate actions, but don't change state?
# should be pure functions? should use another state, more global
    def handle_free_state(self):
        if self.want_trade() and not self.restrictions():
            return Action("new")
        return None

    def handle_new_state(self):
        if not self.want_trade() or self.price_changing_is_big() or self.restrictions():
            return Action("cancel")
        return None

# goal changers:
    def __call__(self, price, amount):
        self.desire.price = price
        self.desire.price = amount

    def update(self, price, amount):
        self.desire.price = price
        self.desire.price = amount

# for main loop
    def do(self, event):
        if not self.is_settings_loaded:
            return

        action = None

        if self.state.status == OrderStatus.FREE:
            action = self.handle_free_state()
        elif self.state.status == OrderStatus.NEW:
            action = self.handle_new_state()
        elif self.state.status == OrderStatus.PENDING_NEW:
            pass
        elif self.state.status == OrderStatus.PENDING_CANCEL:
            pass
        elif self.state.status == OrderStatus.CANCELED:
            pass

        #action = self.genereate_action_from_state(self.state)
        #event is None do nothing
        #event is price amount update
        #event is reply do get_next_state_from_reply
        #event is timer do get_next_state_from_timer

        if action:
            self.state, order = self.next_state_and_order(self.state, self.desire, action) #immutability
            if order:
                yield order







#еще внедрим идею virtualRoboDOM и будет полный фарш!
class Robo(BaseRobo):
    def __init__(self, name):
        super().__init__( name)
        self.initialization()




    def initialization(self):
        self.si = self.id("Si-3.19")
        self.trade_state = "run"
        self.shot = False
        #self.long = long(Si-3.19)
        #self.short = short(Si-3.19)
        #self.si_mm = mm(Si-3.19)

    def update(self, action, payload):
        #self.si_mm(long_price, short_price, max_money_postion, open_amount, position)
        #self.rts_mm(long_price, short_price, max_money_position, amount, postion)

        if self.trade_state == 'stop':
            pass
        elif self.trade_state == 'run':
            buy = {
                "exchange": "moex",
                "type": "new",
                "symbol": "Si-3.19",
                "amount": "1",
                "side": "BUY",
                "price":"64000"
            }
            sell = {
                "exchange": "moex",
                "type": "new",
                "symbol": "Si-3.19",
                "amount": "1",
                "side": "SELL",
                "price": "69000"
            }
            if not self.shot:
                #self.pub(buy)
                #self.pub(sell)
                self.shot = True

            pass

        return self.commands


def run():
    #data = threading.Thread(target=data_stream, args=(["Si-3.19"], db_services['moex-forts'],))
    data = threading.Thread(target=data_stream, args=(robo.symbols, db_services['moex-forts'],))
    #trade = threading.Thread(target=trade_stream, args=(robo_name, db_services['mongodb'],))
    trade = threading.Thread(target=trade_stream, args=(robo.name, db_services['mongodb'],))
    #control = threading.Thread(target=control_stream, args=(robo_name, db_services['mongodb'],))
    control = threading.Thread(target=control_stream, args=(robo.name, db_services['mongodb'],))

    data.daemon = True
    trade.daemon = True
    control.daemon = True

    data.start()
    trade.start()
    control.start()

    robo_loop()


robo = Robo("robo")
print(robo.name)


def main():

    print(robo.symbols)
    #exit(0)
    if setup():
        run()

    cleanup()


if __name__ == "__main__":
    main()
