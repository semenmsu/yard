from algo.order import *
from algo.events import *
from algo.data_source import *
from algo.timers import *


def add_child(to, child):
    if hasattr(to, '__add_child__'):
        print("want add child")
        to.__add_child__(child)
    else:
        print("can't add child")


class Root:
    def __init__(self, store):
        self.__childs = []
        self.store = store
        self.ext_id = 0
        self.nodes_by_extid = dict()  # ext_id
        self.nodes_by_orderid = dict()
        self.trade_callbacks = []
        self.location = "/"

    def __add_child__(self, child):
        self.__childs.append(child)

    def __add_data_source__(self, data_source):
        if hasattr(self, 'data_source'):
            raise Exception("can't add more then one data_source")

        self.data_source = data_source

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index == len(self.__childs):
            raise StopIteration
        child = self.__childs[self.index]
        self.index += 1
        return child

    def __repr__(self):
        repr = ""
        for child in self.__childs:
            repr += str(child)+"\n"
        return repr

    def add(self):
        pass

    def processed_action(self, action):
        if action:
            if isinstance(action, NewOrder):
                source = action.source
                self.ext_id += 1
                self.nodes_by_extid[self.ext_id] = source
                action.ext_id = self.ext_id
            elif isinstance(action, ReleaseOrder):
                return None
        return action

    def on(self, event, callback, filter=None):
        if event == 'trade':
            if not callback in self.trade_callbacks:
                if filter:
                    def filtred_callback(trade):
                        if filter(trade):
                            callback(trade)
                    self.trade_callbacks.append(callback)
                else:
                    self.trade_callbacks.append(callback)

    def do(self, event=None):

        if isinstance(event, DataEvent):
            for action in self.store.update(event):
                if self.processed_action(action):
                    del action.source
                    yield action
        else:
            node = None
            if isinstance(event, NewReplyEvent):
                if event.ext_id in self.nodes_by_extid:

                    node = self.nodes_by_extid[event.ext_id]
                    if event.code == 0:
                        self.nodes_by_orderid[event.order_id] = node
                    del self.nodes_by_extid[event.ext_id]
                else:
                    raise Exception(
                        "can't find node with ext_id", event.ext_id)
            elif isinstance(event, CancelReplyEvent):
                if event.order_id in self.nodes_by_orderid:
                    node = self.nodes_by_orderid[event.order_id]
                else:
                    raise Exception(
                        "can't find node with order_id", event.order_id)
            elif isinstance(event, TradeReplyEvent):
                if event.order_id in self.nodes_by_orderid:
                    node = self.nodes_by_orderid[event.order_id]
                else:
                    raise Exception(
                        "can't find node with order_id", event.order_id)

            else:
                raise Exception("Unknown reply event", event)

            for action in node.do2(event):
                if self.processed_action(action):
                    del action.source
                    yield action

            if isinstance(event, TradeReplyEvent):
                for callback in self.trade_callbacks:
                    callback(event)


class Root2:
    def __init__(self, machine_name, runner_name):
        self.childs = []
        self.strategies = {}
        self.machine = machine_name
        self.name = runner_name
        self.store = DataSource()
        self.timers = Timers()

        self.ext_id = 0
        self.nodes_by_extid = dict()  # ext_id
        self.nodes_by_orderid = dict()
        self.trade_callbacks = []
        self.location = "/"

    def add(self, child):
        child.add_to_parent(self)
        print("child name: ", child.name)
        self.strategies[child.name] = child
        self.timers.subscribe('5s', child.update)
        self.childs.append(child)


    def control(self, control_message):
        if control_message.command() == "start":
            name = control_message.message['name']
            for child in self.childs:
                if child.name == name:
                    child.control(control_message)
        elif control_message.command() == "stop":
            name = control_message.message['name']
            for child in self.childs:
                if child.name == name:
                    print("stop command for", child.name)
                    child.control(control_message)
        elif control_message.command() == "params":
            #print("handle params command")
            name = control_message.message['name']
            for child in self.childs:
                if child.name == name:
                    #print("params command for", child.name)
                    child.control(control_message)

    def get_snapshot(self):
        d = dict()
        d['machine'] = self.machine
        d['runner'] = self.name
        strategies = []
        for child in self.childs:
            strategies.append(child.get_snapshot())
        d['strategies'] = strategies
        return d

    def show(self):
        #for strategy in self.get_snapshot()["strategies"]:
        #    print("name: %s profit: %d position %d" % (
        #        strategy["name"], int(strategy["profit"])/1000000, strategy["position"]))
        return self.get_snapshot()["strategies"]

    def get_state(self):
        root_state = {}
        for child in self.childs:
            root_state[child.name] = child.get_state()
            # print(child.get_state())
        return root_state

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

    def get_symbols(self):
        return self.store.get_symbols()

    def add_symbol_config(self, config):
        self.store.add_symbol_config(config)

    def print_instruments(self):
        self.store.print_instruments()

    def processed_action(self, action):
        if action:
            if isinstance(action, NewOrder):
                source = action.source
                self.ext_id += 1
                self.nodes_by_extid[self.ext_id] = source
                action.ext_id = self.ext_id
            elif isinstance(action, ReleaseOrder):
                return None
        return action

    def on(self, event, callback, filter=None):
        if event == 'trade':
            if not callback in self.trade_callbacks:
                if filter:
                    def filtred_callback(trade):
                        if filter(trade):
                            callback(trade)
                    self.trade_callbacks.append(callback)
                else:
                    self.trade_callbacks.append(callback)

    def do(self, event=None):

        if isinstance(event, DataEvent):
            for action in self.store.update(event):
                if self.processed_action(action):
                    del action.source
                    yield action
        elif isinstance(event, TimeEvent):
            #print("time event NOT IMPLEMENTED")
            # self.timers.update(event)
            # return
            for action in self.timers.update(event):
                if self.processed_action(action):
                    del action.source
                    yield action
        else:
            node = None
            if isinstance(event, NewReplyEvent):
                if event.ext_id in self.nodes_by_extid:

                    node = self.nodes_by_extid[event.ext_id]
                    if event.code == 0:
                        self.nodes_by_orderid[event.order_id] = node
                    del self.nodes_by_extid[event.ext_id]
                else:
                    raise Exception(
                        "can't find node with ext_id", event.ext_id)
            elif isinstance(event, CancelReplyEvent):
                if event.order_id in self.nodes_by_orderid:
                    node = self.nodes_by_orderid[event.order_id]
                else:
                    raise Exception(
                        "can't find node with order_id", event.order_id)
            elif isinstance(event, TradeReplyEvent):
                if event.order_id in self.nodes_by_orderid:
                    node = self.nodes_by_orderid[event.order_id]
                else:
                    raise Exception(
                        "can't find node with order_id", event.order_id)

            else:
                raise Exception("Unknown reply event", event)

            for action in node.do2(event):
                if self.processed_action(action):
                    del action.source
                    yield action

            if isinstance(event, TradeReplyEvent):
                for callback in self.trade_callbacks:
                    callback(event)
