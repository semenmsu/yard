from enum import Enum
import copy
from algo.utils import *
from algo.events import *


class OrderState:

    def __init__(self, dir):
        self.ext_id = 0
        self.order_id = 0  # ?
        self.price = 0
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

    def toDict(self, robo_name, to):
        d = {"from": robo_name, "to": to, "type": self.name, "price": str(self.price), "amount": str(self.amount),
             "side": str(self.dir), "symbol": self.symbol, "ext_id": str(self.ext_id)}
        return d

    def __repr__(self):
        ret = f"price={self.price} amount={self.amount} dir={self.dir} vid={self.vid} ext_id={self.ext_id}"
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

    def toDict(self, robo_name, to):
        d = {"from": robo_name, "to": to, "type": self.name,
             "order_id": str(self.order_id)}
        return d

    def __repr__(self):
        ret = f"order_id={self.order_id} vid={self.vid} "
        return f"{colors.CANCEL_ORDER} CANCEL_ORDER {colors.ACTION}  {ret}  {colors.ENDC}"


class ReleaseOrder:
    def __init__(self, vid, order_id):
        self.vid = vid
        self.order_id = order_id

    def __repr__(self):
        ret = f"order_id={self.order_id} vid={self.vid} "
        return f"{colors.CANCEL_ORDER} RELEASE_ORDER {colors.ACTION}  {ret}  {colors.ENDC}"


class Order:

    def __init__(self, instrument, dir, restrictions=None):
        self.name = "long"
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

        if restrictions:
            self.restrictions = restrictions
        else:
            self.restrictions = lambda: False

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
        if abs(self.desire.price - self.state.price) > self.change_price_limit:
            return True
        return False

    def should_update_price(self, price, amount):
        if abs(price - self.state.price) > self.change_price_limit:
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
            next_state.price = desire.price
            next_state.amount = desire.amount
            next_state.rest_amount = desire.amount
            next_state.inc()
            order = self.generate_new_order(next_state)
            order.symbol = self.instrument.symbol
            return next_state, order

        elif action.name == "cancel":
            next_state = copy.copy(state)
            next_state.status = PENDING_CANCEL
            next_state.inc()
            cancel = self.generate_cancel_order(next_state)
            cancel.symbol = self.instrument.symbol
            return next_state, cancel

    def reply_new(self, new_reply):
        if new_reply.code != 0:
            raise Exception("new_reply.code != 0. Not Implemented")
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
        #print("reply trade",deal)
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
