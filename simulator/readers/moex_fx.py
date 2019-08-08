class MoexFxTradesReaderCSV:
    class TradeCsv:
        def __init__(self, line):
            # SecurityID,MDUpdateAction,MDEntryType,SettleType,MDEntryTime,SendingTime,PacketTime,price,size,side,PriceType,TradingSessionID,TradingSessionSubID
            # USD000UTSTOM,0,z,T1,1550837996907486000,1550837996907839000,1550837996903155000,65585000,20000000,B,0,CNGD,N
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
            trade = MoexFxTradesReaderCSV.TradeCsv(line)
            if trade.symbol:
                if self.symbol:
                    if trade.symbol == self.symbol and trade.trading_session_id == "CETS":
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


class MoexFxStatsReaderCSV:
    class StatsCsv:
        def __init__(self, line):
            values = line.split(',')
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
            trade = MoexFxStatsReaderCSV.StatsCsv(line)
            if trade.symbol:
                if self.symbol:
                    if trade.symbol == self.symbol and trade.trading_session_id == "CETS":
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
