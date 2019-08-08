class MoexEqTradesReaderCSV:
    class TradeCsv:
        def __init__(self, line):
            # EUR_RUB__TOM,1563519903876516000,1563519903876842000,1563519903804029000,70762500,1000000,S
            # print(line)
            values = line.split(',')
            if len(values) > 5:
                self.symbol = values[0]
                self.md_update_action = values[1]
                self.md_entry_type = values[2]
                self.md_settle_type = values[3]
                self.ts = int(values[4])
                self.price = int(values[7])
                self.amount = int(values[8])
                if values[9] == "B":
                    self.dir = 1
                elif values[9] == "S":
                    self.dir = 2
                else:
                    raise Exception("wrong direction", values[9])
                self.trading_session_id = values[11]

                self.type = "trade"
            else:
                self.symbol = None

        def __repr__(self):
            return f"fx_trade_csv {self.ts} {self.symbol} dir={self.dir} price={self.price}"

    def __init__(self, path, symbol_config=None):
        self.file = None
        self.path = path
        exchange_, symbol_ = symbol_config["symbol"].split('@')
        self.symbol = symbol_

    def __iter__(self):
        return self

    def __next__(self):
        for line in self.file:
            trade = MoexEqTradesReaderCSV.TradeCsv(line)
            if trade.symbol:
                if self.symbol:
                    if trade.symbol == self.symbol and trade.trading_session_id == "TQBR":
                        return trade
                else:
                    return trade
            else:
                break
        raise StopIteration()

    def __enter__(self):
        self.file = open(self.path)
        self.file.readline()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.file.close()


class MoexEqStatsReaderCSV:
    class StatsCsv:
        def __init__(self, line):
            values = line.split(',')
            #1081755,EURUSD000TOM,bid,1,1550837926268121000,1550837926268455000,1550837926264454000,1133160,2000000000,C,CETS,
            if len(values) > 7:
                self.symbol = values[1]
                self.dir = 1 if values[2] == "bid" else 2
                self.action = values[3]
                self.ts = int(values[4])
                self.price = int(values[7])
                self.amount = int(values[8])
                self.type = "bidask"
                self.trading_session_id = values[10]
            else:
                self.symbol = None

        def __repr__(self):
            return f"fx_stats_csv {self.ts} {self.symbol} dir={self.dir} action={self.action} price={self.price}"

    def __init__(self, path, symbol_config=None):
        self.file = None
        self.path = path
        exchange_, symbol_ = symbol_config["symbol"].split('@')
        self.symbol = symbol_

    def __iter__(self):
        return self

    def __next__(self):
        for line in self.file:
            trade = MoexEqStatsReaderCSV.StatsCsv(line)
            if trade.symbol:
                if self.symbol:
                    if trade.symbol == self.symbol and trade.trading_session_id == "TQBR":
                        return trade
                else:
                    return trade
            else:
                break
        raise StopIteration()

    def __enter__(self):
        self.file = open(self.path)
        self.file.readline()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.file.close()
