import json
from algo.events import *
from algo.root import *
from algo.nanit import *
from pymongo import MongoClient

instruments = {}
exchange_cache = {}


def get_json_from_line(line):
    json_line = line.replace("'", "\"")
    d = json.loads(line.replace("'", "\""))
    return d


def get_event_from_json(message):
    # print(message["type"])
    t = message["type"]
    if t == "data":
        event = DataEvent.from_json(message["body"])
        #print("This is data event", event)
        return event
    elif t == "order":
        #print("This is order")
        return None
        return event
    elif t == "new_reply":
        event = NewReplyEvent.from_json(message["body"])
        #print("this is new_reply", event)
        return event
    elif t == "cancel_reply":
        event = CancelReplyEvent.from_json(message["body"])
        #print("this is cancel_reply", event)
        return event
    elif t == "trade_reply":
        event = TradeReplyEvent.from_json(message["body"])
        #print("this is trade_reply", event)
        return event
    elif t == "timer":
        event = TimeEvent.from_json(message["body"])
        #print("This is timer", event)
        return event
    elif t == "control":
        event = ControlMessage.from_json(message["body"])
        print("This is control", event)
        return event
    else:
        print("unknow type ", t)
        raise Exception("unknow message")


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
        #robo = TestRobo(control.message["name"])
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


'''
def read_events2(root):
    with open("log/messages-12.txt", "r") as f:
        for line in f:
            #json_line = line.replace("'", "\"")
            # print(json_line)
            #d = json.loads(line.replace("'", "\""))
            # print(d["ts"])
            d = get_json_from_line(line)
            # print(d["ts"])
            event = get_event_from_json(d)
            if event:
                # if not isinstance(event, DataEvent) and not isinstance(event, TimeEvent):
                #    print(event)
                print("line", line)
                print(event)
                if isinstance(event, ControlMessage):
                    handle_control(root, event)
                    #snapshot = root.get_snapshot()
                    # publish_snapshot(snapshot)
                    continue

                if isinstance(event, TimeEvent):
                    # f.flush()
                    #snapshot = root.get_snapshot()
                    # publish_snapshot(snapshot)
                    pass

                for order in root.do(event):
                    #event, state, order
                    print(order)
                    print(root.get_state())
                    input("Press Enter to continue...")
'''


def read_events(root):
    events = []
    with open("log/messages-12.txt", "r") as f:
        for line in f:
            d = get_json_from_line(line)
            event = get_event_from_json(d)
            if event:
                events.append(event)

    for event in events:
        if event:
            print(event)
            if isinstance(event, ControlMessage):
                handle_control(root, event)
                continue

            if isinstance(event, TimeEvent):
                pass

            for order in root.do(event):
                #event, state, order
                print(order)
                print(root.get_state())
                input("Press Enter to continue...")


def run_simulation():
    root = Root2("ubuntu", "robo")
    robo_config = {"name": "mm-si", "type": "Nanit", "symbol": "moex@Si-9.19", "buy_limit": "1", "buy_by": "1",
                   "sell_limit": "-1", "sell_by": 1}
    robo = create_robo_from_config(robo_config)
    root.add(robo)
    input("Press button...")
    for symbol in root.get_symbols():
        find_instrument_and_subscribe(root, symbol)

    read_events(root)


run_simulation()

'''
root = Root2("ubuntu", "robo")
    #robo = TestRobo("spreader")
    # root.add(robo)
    load_config(root)
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')
    publish_snapshot = get_snapshot_publisher()
    orders = []
    publish = get_orders_publisher()
    with open("log/messages.txt", "w") as f:
        while True:
            # event = receiver.recv_json()

            event = receiver.recv_pyobj()
            f.write(
                str({"ts": int(time.time()*1000000), "type": get_event_type(event),  "body": event.__dict__})+"\n")
            if not isinstance(event, DataEvent) and not isinstance(event, TimeEvent):
                print(event)
            if isinstance(event, ControlMessage):
                handle_control(root, event)
                snapshot = root.get_snapshot()
                publish_snapshot(snapshot)
                continue

            if isinstance(event, TimeEvent):
                f.flush()
                snapshot = root.get_snapshot()
                publish_snapshot(snapshot)

            for order in root.do(event):
                print("order: ", order)
                orders.append(order)
                f.write(str({
                    "ts": int(time.time()*1000000), "type": "order", "body": order.__dict__
                })+"\n")
            publish(orders)
            orders = []
'''
