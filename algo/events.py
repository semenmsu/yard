from enum import Enum
import copy
from algo.utils import *


class DataEvent:
    def __init__(self, symbol, price):
        self.symbol = symbol
        self.price = price

    def from_json(d):
        symbol = d["symbol"]
        price = int(d["price"])
        return DataEvent(symbol, price)

    def __repr__(self):
        ret = f"price={self.price} symbol={self.symbol}"
        return f"{colors.DATA_EVENT} DATA_EVENT {colors.EVENT}  {ret}{colors.ENDC}"


class ControlEvent:
    def __init__(self, ctrl, to, params):
        self.params = params
        self.to = to
        self.ctrl = ctrl


class ControlMessage:
    def __init__(self, message):
        self.message = message

    def from_json(d):
        event = ControlMessage(d["message"])
        return event

    def __repr__(self):
        return f"{self.ts} {self.message}"

    def command(self):
        return self.message['command']


class NewReplyEvent:
    def __init__(self, code, order_id):
        self.name = "new_reply"
        self.code = int(code)
        self.order_id = int(order_id)
        self.ext_id = 0
        self.message = None

    def from_json(d):
        # {'name': 'new_reply', 'code': 0, 'order_id': 2311185157, 'ext_id': 1, 'message': 'Operation successful.'}
        code = d["code"]
        order_id = d["order_id"]
        ext_id = int(d["ext_id"])
        message = d["message"]
        event = NewReplyEvent(code, order_id)
        event.ext_id = ext_id
        event.message = message
        return event

    def __repr__(self):
        ret = f"code={self.code} order_id={self.order_id} ext_id={self.ext_id} message={self.message}"
        return f"{colors.DATA_EVENT} NEW_REPLY_EVENT{colors.EVENT}  {ret}  {colors.ENDC}"


class CancelReplyEvent:
    def __init__(self, code, amount):
        self.name = "cancel_reply"
        self.code = int(code)
        self.order_id = 0
        self.amount = int(amount)

    def from_json(d):
        code = d["code"]
        amount = d["amount"]
        order_id = int(d["order_id"])
        event = CancelReplyEvent(code, amount)
        event.order_id = order_id
        return event

    def __repr__(self):
        ret = f"code={self.code} amount={self.amount} "
        return f"{colors.DATA_EVENT} CANCEL_REPLY_EVENT {colors.EVENT}  {ret} {colors.ENDC}"


class TradeReplyEvent:
    def __init__(self, amount, deal_price):
        self.name = "trade_reply"
        self.amount = int(amount)
        self.deal_price = int(deal_price)
        self.order_id = 0
        self.deal_id = 0
        self.dir = 0
        self.symbol = ""

    def money(self):
        return self.amount * self.deal_price

    def from_json(d):
        amount = d["amount"]
        deal_price = d["deal_price"]
        order_id = int(d["order_id"])
        deal_id = int(d["deal_id"])
        event = TradeReplyEvent(amount, deal_price)
        event.order_id = order_id
        event.deal_id = deal_id
        return event

    def __repr__(self):
        ret = f"deal_price={self.deal_price} amount={self.amount}"
        return f"{colors.EVENT} TRADE_EVENT   {ret} {colors.ENDC}"

    def get_csv(self):
        return f"{self.symbol},{self.dir},{self.deal_price},{self.amount},{self.order_id},"


class DataOrderEvent:
    def __init__(self, price, amount):
        self.name = "data"
        self.price = price
        self.amount = amount

    def __repr__(self):
        ret = f"price={self.price} amount={self.amount}"
        return f"{colors.DATA_EVENT} DATA_EVENT {colors.EVENT}  {ret}{colors.ENDC}"


class SettingsEvent:
    def __init__(self, settings):
        self.name = "settings"
        self.settings = settings


class TimeEvent:
    def __init__(self, time):
        self.name = "timer"
        self.time = time
        self.type = None

    def from_json(d):
        # {'name': 'timer', 'time': 1562922729.984771, 'type': '5s'}}
        t = float(d["time"])
        _type = d["type"]
        event = TimeEvent(t)
        event.type = _type
        return event

    def __repr__(self):
        return f"[data-event] {self.time} type = {self.type}"
