from enum import Enum
import copy
from algo.utils import *
from algo.events import *


class OrderState:

    def __init__(self, dir):
        self.ext_id = 0
        self.order_id = 0  # ?
        self.price = 0
        self.price_i = 0
        self.amount = 0
        self.rest_amount = 0
        self.dir = dir
        self.status = FREE
        self.sending_time = 0
        self.create_time = 0
        self.last_code = 0
        self._state_id = 0

    def free(self):
        self.status = FREE
        self.order_id = 0
        self.amount = 0
        self.price = 0
        self.price_i = 0
        self.rest_amount = 0
        self.sending_time = 0
        self.create_time = 0
        self.last_code = 0

    def inc(self):
        self._state_id += 1

    def __repr__(self):
        status_str = order_status_to_str(self.status)
        ret = f"status={status_str} order_id={self.order_id} price={self.price} amount={self.amount} rest_amount={self.rest_amount} id={self._state_id}"
        return f"{colors.STATE}  {ret} {colors.ENDC}"


class OrderDesire:
    def __init__(self):
        self.price = 0
        self.amount = 0


class Action:
    def __init__(self, name):
        self.name = name


class NewOrder:
    def __init__(self, isin_id, dir):
        self.name = "new_order"
        self.user_code = 1
        self.isin_id = isin_id
        self.symbol = None
        self.ext_id = 0
        self.price = 0
        self.amount = 0
        self.dir = dir
        self.vid = 0
        self.source = None

    def from_json(d):
        # {'name': 'new_order', 'user_code': 1, 'isin_id': 1, 'symbol': 'Si-9.19', 'ext_id': 2, 'price': 63628, 'amount': 1, 'dir': 2, 'vid': 0}}
        order = NewOrder(int(d["isin_id"]), int(d["dir"]))
        order.user_code = d['user_code']
        order.symbol = d["symbol"]
        order.ext_id = d["ext_id"]
        order.price = d["price"]
        order.amount = d["amount"]
        order.vid = d["vid"]
        return order

    def compare(self, that):
        # price=63615 amount=1 dir=1 vid=0 ext_id=65
        if self.price != that.price:
            return 0

        if self.amount != that.amount:
            return 0

        if self.dir != that.dir:
            return 0

        if self.vid != self.vid:
            return 0

        if self.ext_id != that.ext_id:
            return 0

        return 1

    def toDict(self, robo_name, to):
        d = {"from": robo_name, "to": to, "type": self.name, "price": str(self.price), "amount": str(self.amount),
             "side": str(self.dir), "symbol": self.symbol, "ext_id": str(self.ext_id)}
        return d

    def __repr__(self):
        ret = f"symbol={self.symbol} isin_id={self.isin_id} price={self.price} amount={self.amount} dir={self.dir} vid={self.vid} ext_id={self.ext_id}"
        return f"{colors.NEW_ORDER}  NEW_ORDER {colors.ACTION}  {ret}  {colors.ENDC}"


class CancelOrder:
    def __init__(self, isin_id):
        self.name = "cancel_order"
        self.isin_id = isin_id
        self.user_code = 1
        self.order_id = 0
        self.vid = 0
        self.source = None
        self.symbol = None

    def from_json(d):
        #{'name': 'cancel_order', 'isin_id': 1, 'user_code': 1, 'order_id': 2311185157, 'vid': 0, 'symbol': 'Si-9.19'}
        order = CancelOrder(int(d["isin_id"]))
        order.user_code = d["user_code"]
        order.order_id = d["order_id"]
        order.vid = d["vid"]
        order.symbol = d["symbol"]
        return order

    def compare(self, that):
        # order_id=2311213677 vid=0
        if self.order_id != that.order_id:
            return 0

        if self.vid != that.vid:
            return 0

        return 1

    def toDict(self, robo_name, to):
        d = {"from": robo_name, "to": to, "type": self.name,
             "order_id": str(self.order_id)}
        return d

    def __repr__(self):
        ret = f"order_id={self.order_id} vid={self.vid} "
        return f"{colors.CANCEL_ORDER} CANCEL_ORDER {colors.ACTION}  {ret}  {colors.ENDC}"


def create_order_from_json(message):
    name = message["name"]
    if name == "new_order":
        #{'name': 'new_order', 'user_code': 1, 'isin_id': 1, 'symbol': 'Si-9.19', 'ext_id': 1, 'price': 63620, 'amount': 1, 'dir': 1, 'vid': 0}
        order = NewOrder(message['isin_id'], message['dir'])
        order.user_code = message["user_code"]
        order.symbol = message["symbol"]
        order.ext_id = message["ext_id"]
        order.price = message["price"]
        order.amount = message["amount"]
        order.vid = message["vid"]
        return order
    elif name == "cancel_order":
        #{'name': 'cancel_order', 'isin_id': 1, 'user_code': 1, 'order_id': 2311185157, 'vid': 0, 'symbol': 'Si-9.19'}
        pass


class ReleaseOrder:
    def __init__(self, vid, order_id):
        self.vid = vid
        self.order_id = order_id

    def __repr__(self):
        ret = f"order_id={self.order_id} vid={self.vid} "
        return f"{colors.CANCEL_ORDER} RELEASE_ORDER {colors.ACTION}  {ret}  {colors.ENDC}"


class Order:

    def __init__(self, instrument, dir, restrictions=None):
        if dir == 1:
            self.name = "long"
        else:
            self.name = "short"
        self.instrument = instrument
        self.state = OrderState(dir)
        self.desire = OrderDesire()
        self.session_id = 0
        self.total_money = 0
        self.total_trades = 0
        self.is_settings_loaded = 0
        self.min_step_price = 1
        self.isin_id = 1
        self.change_price_limit = 2  # custom settings
        self.dir = dir
        self.time = 0
        self.vid = 0  # virtual id
        self.code = 0
        self.message = 0
        if restrictions:
            self.restrictions = restrictions
        else:
            self.restrictions = lambda: False

    def get_snapshot(self):
        d = dict()
        d = self.state.__dict__
        # print(d)
        #print("self.instrument", self.instrument)
        d['symbol'] = self.instrument.symbol
        d['ex_symbol'] = self.instrument.ex_symbol
        d['name'] = self.name
        d['order_id'] = self.state.order_id
        d['ext_id'] = self.state.ext_id
        if self.state.status == UNHANDLED_NEW_REPLY_CODE:
            d['code'] = self.code
            d['message'] = self.message

        return d

    def get_state(self):
        d = dict()
        d['state'] = self.state.__dict__
        d['vid'] = self.vid
        d['code'] = self.code
        d['message'] = self.message
        return d


# utils


    def generate_new_order(self, state):
        order = NewOrder(self.isin_id, self.dir)
        order.price = state.price
        order.amount = state.amount
        order.vid = self.vid
        return order

    def generate_cancel_order(self, state):
        cancel = CancelOrder(self.isin_id)
        cancel.order_id = state.order_id
        cancel.vid = self.vid
        return cancel

    def price_changing_is_big(self):
        if abs(self.desire.price - self.state.price_i) > self.change_price_limit*self.instrument.min_step_price_i:
            return True
        return False

    def should_update_price(self, price, amount):
        if abs(price - self.state.price_i) > self.change_price_limit*self.instrument.min_step_price_i:
            return True

        if self.state.amount > 0 and amount == 0:  # should cancel
            return True
        return False

    def want_trade(self):
        return self.desire.amount > 0

# state changers:
    def next_state_and_order(self, state, desire, action):
        if action.name == "new":
            next_state = copy.copy(state)
            next_state.status = PENDING_NEW
            #next_state.price = desire.price
            next_state.price_i = desire.price
            next_state.price = self.instrument.get_real_price(desire.price)
            next_state.amount = desire.amount
            next_state.rest_amount = desire.amount
            next_state.inc()
            order = self.generate_new_order(next_state)
            order.symbol = self.instrument.symbol
            #order.symbol = self.instrument.ex_symbol
            return next_state, order

        elif action.name == "cancel":
            next_state = copy.copy(state)
            next_state.status = PENDING_CANCEL
            next_state.inc()
            cancel = self.generate_cancel_order(next_state)
            cancel.symbol = self.instrument.symbol
            #cancel.symbol = self.instrument.ex_symbol
            return next_state, cancel

    def reply_new(self, new_reply):
        if new_reply.code != 0:
            if new_reply.code == 31:
                self.state.free()
                self.state.inc()
            else:
                #raise Exception("new_reply.code != 0. Not Implemented")
                self.state.status = UNHANDLED_NEW_REPLY_CODE
                self.code = new_reply.code
                self.message = new_reply.message
                self.state.inc()
        else:
            self.state.order_id = new_reply.order_id
            self.state.status = NEW
            self.state.inc()

    def reply_cancel(self, cancel_reply):
        order_id = self.state.order_id
        if cancel_reply.code == 0:
            self.state.rest_amount -= cancel_reply.amount

            if self.state.rest_amount == 0:
                self.state.free()
            else:
                self.state.status = CANCELED
        else:
            if self.state.rest_amount > 0:
                self.state.status = CANCELED
            else:
                self.state.free()

        self.state.inc()

        if self.state.status == FREE:
            return ReleaseOrder(self.vid, order_id)

    def reply_trade(self, deal):
        #print("reply trade", deal)
        self.state.rest_amount -= deal.amount
        self.total_money += deal.money()
        self.total_trades += deal.amount
        order_id = self.state.order_id

        if self.state.rest_amount == 0:
            self.state.free()

        self.state.inc()

        if self.state.status == FREE:
            return ReleaseOrder(self.vid, order_id)

    def load_settings(self, settings):
        if not self.is_settings_loaded:
            pass  # load settings
            self.is_settings_loaded = True

    def update_time(self, time_event):
        self.time = time_event.time


# generate actions, but don't change state?
# should be pure functions? should use another state, more global


    def handle_free_state(self):
        # print("hande_free_state")
        if self.want_trade() and not self.restrictions():
            return Action("new")
        return None

    def handle_new_state(self):
        # print("hande_new_state")
        if not self.want_trade() or self.price_changing_is_big() or self.restrictions():
            return Action("cancel")
        return None

# goal changers:
    def __call__(self, price, amount):
        self.desire.price = price
        self.desire.price = amount

    def update(self, price, amount):
        #print(f"update new_price = {price} new_amount={amount}")
        self.desire.price = price
        self.desire.amount = amount

    def stop(self):
        self.update(0, 0)

# for main loop

    def generate_action(self):
        action = None
        #print("generate action")

        if self.state.status == FREE:
            action = self.handle_free_state()
        elif self.state.status == NEW:
            action = self.handle_new_state()
        elif self.state.status == PENDING_NEW:
            pass  # if pending_new_to_long do something? may be it is work for supervisor
            # idea if PENDING and state.id havn't change for long time,  run supervisor worker handler
        elif self.state.status == PENDING_CANCEL:
            pass
        elif self.state.status == CANCELED:
            pass
        elif self.state.status == UNHANDLED_CANCEL_REPLY_CODE:
            pass
        elif self.state.status == UNHANDLED_NEW_REPLY_CODE:
            pass

        return action

    def do2(self, event=None):
        action = None

        if isinstance(event, DataOrderEvent):
            self.update(event.price, event.amount)
        elif isinstance(event, TimeEvent):
            self.update_time(event)
        elif isinstance(event, SettingsEvent):
            self.load_settings(event)
        elif isinstance(event, NewReplyEvent):
            self.reply_new(event)
        elif isinstance(event, CancelReplyEvent):
            action = self.reply_cancel(event)
        elif isinstance(event, TradeReplyEvent):
            action = self.reply_trade(event)

        if action:
            yield action

        # should robo react? (what to do for move from state to desire)
        action = self.generate_action()

        if action:
            self.state, order = self.next_state_and_order(
                self.state, self.desire, action)  # immutability
            if order:
                order.source = self
                yield order
