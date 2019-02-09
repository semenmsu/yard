trade framework for practical use

### Торговая часть

- **robo_loop** основной поток имеет цикл, где слушает входящие сообщения (используется zmq)
- **data_stream** - запускается в отдельном потоке, слушает сообщения о цена и данных инструментов и пересыkает их в основной поток
- **control_stream** - запускается в отдельном потоке, слушает сообщения по управлению и пересылает их в основной поток
- **trade_stream** - запускается в отдельном потоке, слушает все сообщения по ордерам и пересыkает их в основной поток

Для производительности используется внутри робота протоколо _inproc://_, канал **inproc://robo**

Пример запуска

```python
import threading
data = threading.Thread(target=data_stream, args(["Si-3.19", "RTS-3.19"], settings)
```

Пример простого связывания потоков обрабтки и основного цикла

```python
import zmq

shared_context = zmq.Context()

def data_stream(symbols=[], settings={}):
    sender = shared_context.socket(zmq.PUB)
    sender.connect("inproc://robo")
    data_service = shared_context.socket(zmq.SUB)
    data_service.connect("tcp://localhost:5561")

    for symbol in symbols:
        to_bytes = bytes(symbol,"ascii")
        data_service.subscribe(to_bytes)

    while True:
        msg = data_service.recv()
        sender.send_json({'data': msg})

def robo_loop():
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')

    while True:
        msg = receiver.recv_json()
        #... process message and apply to robo

def run():
    data = threading.Thread(target=data_stream, args(["Si-3.19", "RTS-3.19"])
    data.daemon = True
    data.start()
    robo_loop()

run()
```
