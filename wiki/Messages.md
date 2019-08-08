### Message Types

-   data
-   new_order
-   cancel_order
-   new_reply
-   cancel_reply
-   trade_reply
-   timer
-   control (start/stop) - добавление, удаление роботов, параметры, старт, стоп,
-   session_status - о состоянии торговых сессий, клиринге, приостановке торгов
-   system - сообщения о состоянии системы (загрузка процессора, нехватка памяти)

```python
if t == "data":
        event = DataEvent.from_json(message["body"])
        #print("This is data event", event)
        return event
    elif t == "order":
        #print("This is order")
        if message["body"]["name"] == "new_order":
            event = NewOrder.from_json(message["body"])
            return event
        elif message["body"]["name"] == "cancel_order":
            event = CancelOrder.from_json(message["body"])
            return event
        return None
    elif t == "new_reply":
        event = NewReplyEvent.from_json(message["body"])
        #print("this is new_reply", event)
        return event
    elif t == "cancel_reply":
        event = CancelReplyEvent.from_json(message["body"])
        #print("this is cancel_reply", event)
        return event
    elif t == "trade_reply":
        event = TradeReplyEvent.from_json(message["body"])
        #print("this is trade_reply", event)
        return event
    elif t == "timer":
        event = TimeEvent.from_json(message["body"])
        #print("This is timer", event)
        return event
    elif t == "control":
        event = ControlMessage.from_json(message["body"])
        print("This is control", event)
        return event
```
