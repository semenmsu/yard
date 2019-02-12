import __before__
import time
from algo.order import *

import json


def process_order(order):
    _type = order['type']
    #print("type: ", _type)
    if _type == "new":
        action = NewOrder(None, order['dir'])
        action.symbol = order['symbol']
        action.ext_id = order['ext_id']
        action.price = order['price']
        action.amount = order['amount']
        return action
    if _type == "cancel":
        action = CancelOrder(None)
        action.order_id = order['order_id']
        return action
