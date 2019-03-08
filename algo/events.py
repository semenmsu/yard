from enum import Enum
import copy
from algo.utils import *


class DataEvent:
    def __init__(self, symbol, price):
        self.symbol = symbol
        self.price = price

    def __repr__(self):
        ret = f"price={self.price} symbol={self.symbol}"
        return f"{colors.DATA_EVENT} DATA_EVENT {colors.EVENT}  {ret}{colors.ENDC}"


class ControlEvent:
    def __init__(self, ctrl, to, params):
        self.params = params
        self.to = to
        self.ctrl = ctrl


class NewReplyEvent:
    def __init__(self, code, order_id):
        self.name = "new_reply"
        self.code = int(code)
        self.order_id = int(order_id)
        self.ext_id = 0

    def __repr__(self):
        ret = f"code={self.code} order_id={self.order_id} ext_id={self.ext_id}"
        return f"{colors.DATA_EVENT} NEW_REPLY_EVENT{colors.EVENT}  {ret}  {colors.ENDC}"


class CancelReplyEvent:
    def __init__(self, code, amount):
        self.name = "cancel_reply"
        self.code = int(code)
        self.order_id = 0
        self.amount = int(amount)

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

    def money(self):
        return self.amount * self.deal_price

    def __repr__(self):
        ret = f"deal_price={self.deal_price} amount={self.amount}"
        return f"{colors.EVENT} TRADE_EVENT   {ret} {colors.ENDC}"


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

    def __repr__(self):
        return f"[data-event] {self.time}"
