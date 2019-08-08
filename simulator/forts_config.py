from datetime import datetime
import time


class SimulatorConfig:

    def __init__(self):
        self.date = None
        self.strategies = []
        self.control_messages = []
        self.data_sources = None
        self.orders_structs_map = None

    def set_date_yyyymmdd(self, date):
        self.date = date

    def add_strategy_config(self, strategy_config):
        self.strategies.append(strategy_config)

    def add_control_message(self, control_message):
        if not self.date:
            raise Exception("add_control_message: date should be define!")
        # process control_message, define ts correctly
        self.control_messages.append(control_message)

    def get_unix_time_ns(self, hh_mm_ss):
        full_time = self.date+"-"+hh_mm_ss
        print("full_time ", full_time)
        # 1sec = 1000ms = 1_000_000 mks == 1_000_000_000 ns
        return time.mktime(datetime.strptime(full_time, "%Y%m%d-%H:%M:%S").timetuple())*1000_000_000

    def get_datetime_str_from_unix_time_ns(self, unix_ts):
        timestamp = datetime.fromtimestamp(unix_ts/1000_000_000)
        print("time_stamp", timestamp)
        ns = unix_ts % 1000_000_000
        mks = int(ns/1000)
        datetime_str = timestamp.strftime(
            '%Y-%m-%d %H:%M:%S') + "."+str(mks).zfill(6)
        return datetime_str


si_mm_config = {"name": "mm-si", "type": "Nanit", "symbol": "moex_eq@GAZP", "buy_limit": "1", "buy_by": "1",
                "sell_limit": "-1", "sell_by": 1, "buy_shift": 10, "sell_shift": 10}


start_trade_session_control_message = {"ts": "10:06:00", "body": {
    'to': 'robo', 'name': 'mm-si', 'machine': 'ubuntu', 'runner': 'robo', 'command': 'start'}}

one_minute_before_day_clearing_control_message = {"ts": "13:59:00", "body": {
    'to': 'robo', 'name': 'mm-si', 'machine': 'ubuntu', 'runner': 'robo', 'command': 'stop'}}

one_minute_after_day_clearing_control_message = {"ts": "14:06:00", "body": {
    'to': 'robo', 'name': 'mm-si', 'machine': 'ubuntu', 'runner': 'robo', 'command': 'start'}}

stop_trade_session_control_message = {"ts": "18:30:00", "body": {
    'to': 'robo', 'name': 'mm-si', 'machine': 'ubuntu', 'runner': 'robo', 'command': 'stop'}}

config = SimulatorConfig()
config.set_date_yyyymmdd("20190719")
config.add_strategy_config(si_mm_config)
config.add_control_message(start_trade_session_control_message)
config.add_control_message(one_minute_before_day_clearing_control_message)
config.add_control_message(one_minute_after_day_clearing_control_message)
# не работает, порядок видимо не соблюдается
config.add_control_message(stop_trade_session_control_message)
