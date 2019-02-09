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
    #... creaet socket for data, connect to datasource and subscribe
    #...
    while True:
        msg = socket.recv()
        sender.send_json({'data': msg})

def robo_loop():
    receiver = shared_context.socket(zmq.SUB)
    receiver.bind("inproc://robo")
    receiver.subscribe(b'')

    while True:
        msg = receiver.recv_json()
        #... process message and apply to robo
```
