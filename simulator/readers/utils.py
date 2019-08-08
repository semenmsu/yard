def merge_by_ts(*args):
    if not args or len(args) == 0:
        return None
    if len(args) == 1:
        return args[0]

    trade_events = []
    num_exchanges = len(args)
    indexes = [0]*num_exchanges
    total_len = 0
    lens = []
    print("num_exchanges ", num_exchanges)
    print("len", len(args[0]))
    for exchange_trade_events in args:
        total_len += len(exchange_trade_events)
        lens.append(len(exchange_trade_events))

    print("total_len", total_len)
    for i in range(total_len):
        next_entry_times = [None]*num_exchanges
        for j in range(num_exchanges):
            if indexes[j] < lens[j]:
                next_entry_times[j] = args[j][indexes[j]].ts

        # find index with min entry_time and not None
        min_index = 0
        min_value = next_entry_times[0]
        for j in range(1, len(next_entry_times)):
            if not min_value:
                if next_entry_times[j]:
                    min_index = j
                    min_value = next_entry_times[j]
            elif next_entry_times[j]:
                if min_value > next_entry_times[j]:
                    min_index = j
                    min_value = next_entry_times[j]

        if min_value:
            trade_events.append(args[min_index][indexes[min_index]])
            indexes[min_index] += 1

    return trade_events
