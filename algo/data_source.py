import math


class Instrument():
    def __init__(self, symbol):
        self.subscribers = []
        self.price = 0
        self.symbol = symbol
        [exchange, ex_symbol] = self.symbol.split("@")
        self.exchange = exchange
        self.ex_symbol = ex_symbol
        self.is_settings_loaded = 0
        self.min_step_price = None
        self.min_step_price_i = None
        self.roundto = None
        self.isin_id = None
        self.lot_volume = None
        self.price_mult = None
        self.amount_mult = None

    def get_real_price_up(self, price):
        real_price = int(math.ceil(price/self.min_step_price_i)
                         * self.min_step_price_i)/self.price_mult
        real_price = round(real_price, self.roundto)
        return real_price

    def get_real_price_down(self, price):
        real_price = int(math.floor(price/self.min_step_price_i)
                         * self.min_step_price_i)/self.price_mult
        real_price = round(real_price, self.roundto)
        return real_price

    def get_real_price(self, price):
        real_price = (int(price/self.min_step_price_i) *
                      self.min_step_price_i)/self.price_mult
        if self.roundto == 0:
            real_price = int(real_price)
        else:
            real_price = round(real_price, self.roundto)
        return real_price

    def update_property(self, name, value):
        if name == 'min_step':
            self.min_step_price = value
        if name == "min_step_i":
            self.min_step_price_i = value
        if name == 'roundto':
            self.roundto = value
        if name == 'isin_id':
            self.isin_id = value
        if name == 'lot_volume':
            self.lot_volume = value
        if name == "price_mult":
            self.price_mult = value
        if name == "amount_mult":
            self.amount_mult = value

    def __repr__(self):
        return f"symbol = {self.symbol} \
        roundto = {self.roundto}\
        min_step_price={self.min_step_price} isin={self.isin_id} is_settings_loaded = {self.is_settings_loaded}"


class DataSource:
    def __init__(self):
        self.symbols = {}

    def update(self, event):
        if event.symbol in self.symbols:
            self.symbols[event.symbol].price = event.price
            for subscriber in self.symbols[event.symbol].subscribers:
                yield from subscriber.update()

    def subscribe(self, symbol, source):
        if not symbol in self.symbols:
            self.symbols[symbol] = Instrument(symbol)

        if not source in self.symbols[symbol].subscribers:
            self.symbols[symbol].subscribers.append(source)

        return self.symbols[symbol]

    def get_symbols(self):
        return list(self.symbols.keys())

    def get_dom(self):
        uniq_locations = []
        for symbol in self.symbols.keys():
            for subscriber in self.symbols[symbol].subscribers:
                if not subscriber.location in uniq_locations:
                    uniq_locations.append(subscriber.location)
        return uniq_locations

    def add_symbol_config(self, config):
        print("inside add_symbol_config ", config)
        symbol = config['symbol']
        print("find symbol ", symbol)
        instrument = self.symbols[symbol]
        for key, value in config.items():
            instrument.update_property(key, value)

    def print_instruments(self):
        for symbol, instrument in self.symbols.items():
            print(symbol, instrument)
