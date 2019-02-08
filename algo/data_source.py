class Instrument():
    def __init__(self, symbol):
        self.subscribers = []
        self.price = 0
        self.symbol = symbol


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

    def get_dom(self):
        uniq_locations = []
        for symbol in self.symbols.keys():
            for subscriber in self.symbols[symbol].subscribers:
                if not subscriber.location in uniq_locations:
                    uniq_locations.append(subscriber.location)

        return uniq_locations
