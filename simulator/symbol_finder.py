moex_fx = {
    'USD000UTSTOM': {
        "price_mult": 1000000,
        "amount_mult": 1000000,
        "min_step_i": int(0.0025*1000000),
        "isin_id": 1,
        "min_step": 0.0025,
        "step_price": int(0.0025*1000000),
        "roundto": 4,
        "lot_volume": 1000,
        "curr": "RUR"},
    'USD000000TOD':{
        "price_mult": 1000000,
        "amount_mult": 1000000,
        "min_step_i": int(0.0025*1000000),
        "isin_id": 1,
        "min_step": 0.0025,
        "step_price": int(0.0025*1000000),
        "roundto": 4,
        "lot_volume": 1000,
        "curr": "RUR"},
}

moex_eq = {
    "SBER": {
        "price_mult": 1000000,
        "amount_mult": 1000000,
        "min_step_i": int(0.01*1000000),
        "isin_id": 2,
        "min_step": 0.01,
        "step_price": int(0.01*1000000),
        "roundto": 2,
        "lot_volume": 10,
        "curr": "RUR"},
    "GAZP": {
        "price_mult": 1000000,
        "amount_mult": 1000000,
        "min_step_i": int(0.01*1000000),
        "isin_id": 2,
        "min_step": 0.01,
        "step_price": int(0.01*1000000),
        "roundto": 2,
        "lot_volume": 10,
        "curr": "RUR"}
}

# через on_subscribe можно узнать на что подписались стратегии


class SymbolFinder:
    def __init__(self):
        self.instruments = {}
        self.exchanges = {
            'moex_fx': moex_fx,
            'moex_eq': moex_eq,
        }
        self.on_subscirbe = None

    def load_exchange(self, exchange_name, date=None):
        raise Exception(f"can't load {exchange_name}")

    def find(self, exchange_symbol, date=None):
        [exchange, symbol] = exchange_symbol.split('@')
        if exchange in self.exchanges:
            instruments = self.exchanges[exchange]
            if symbol in instruments:
                instrument_config = instruments[symbol]
                instrument_config['symbol'] = exchange_symbol
                return instrument_config
            else:
                raise Exception(f"can't find {symbol} in {exchange}")
        else:
            self.load_exchange(exchange_symbol, date)

    def subscribe(self, root, symbol):
        symbol_config = self.find(symbol)
        root.add_symbol_config(symbol_config)
        if self.on_subscirbe:
            self.on_subscirbe(symbol_config)
        return symbol_config
