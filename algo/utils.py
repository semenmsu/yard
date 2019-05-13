FREE = 1
PENDING_NEW = 2
NEW = 3
PENDING_CANCEL = 4
CANCELED = 5
UNHANDLED_NEW_REPLY_CODE = 6
UNHANDLED_CANCEL_REPLY_CODE = 7

BUY = 1
SELL = 2

status_dict = {FREE: "FREE",
               PENDING_NEW: "PENDING_NEW",
               NEW: "NEW",
               PENDING_CANCEL: "PENDING_CANCEL",
               CANCELED: "CANCELED"}

# \033[Style, TextColor, Background color m, example \033[1;32;40m


class colors:
    HEADER = '\033[95m'
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    STATE = '\033[0;30;47m'
    ACTION = '\033[0;30;46m'
    EVENT = '\033[0;30;42m'
    DATA_EVENT = '\033[0;30;43m'
    NEW_REPLY_EVENT = '\033[0;37;47m'
    NEW_ORDER = '\33[0;37;44m'
    CANCEL_ORDER = '\33[0;37;41m'


def order_status_to_str(status):
    return status_dict[status]
