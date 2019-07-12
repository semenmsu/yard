trade framework for practical use

### Торговая часть

-   **robo_loop** основной поток имеет цикл, где слушает входящие сообщения (используется zmq)
-   **data_stream** - запускается в отдельном потоке, слушает сообщения о цена и данных инструментов и пересыkает их в основной поток
-   **control_stream** - запускается в отдельном потоке, слушает сообщения по управлению и пересылает их в основной поток
-   **trade_stream** - запускается в отдельном потоке, слушает все сообщения по ордерам и пересыkает их в основной поток

Для производительности используется внутри робота протоколо _inproc://_, канал **inproc://robo**

Пример запуска

```python
import threading
data = threading.Thread(target=data_stream, args(["Si-3.19", "RTS-3.19"], settings)
```

Пример простого связывания потоков обрабтки и основного цикла

```python
import zmq
import threading

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

В такой архитектуре мы получаем один поток для всей бизнес логики, в этом потоке отсуствуют проблемы с блокирующими операциями, отсутствуют проблемы с синхронизацией. Потенциально такую архитектуру легко разнести по разным процессам, просто сменив zeromq протокол.

### Orders (медленный вариант)

-   возможность хранить в независимом месте все ордера (One Source of Truth)
-   возможность запускать новых роботов без дополнительных настроек
-   понятный интерфейс для взаимодействия отвязанный от внутренних реализаций
-   надежность, репликация данных
-   возможость проводить анализ без нагрузки на основную систему

Используется MongoDb и change stream для нотификации системы. Замеры показали в районе 1-3мс латенси в системе robo -> order_gateway

Пример:

```python
def trades_stream(robo_name, config={}):
        sender = shared_context.socket(zmq.PUB)
        sender.connect("inproc://robo")
        url = "mongodb://localhost:27017"
        client = MongoClient(url, socketKeepAlive=True)
        pipeline = [
                {"$match": {"fullDocument.name", robo_name, "operationType":"insert"}},
                {"$project": {"fullDocument._id": 0}}
        ]
        options = {}
        db = client.test
        with db.trades.watch(pipeline, **options) as stream:
                for change in stream:
                        sender.send_json('trades': change['fullDocument'])
```

В коде мы подписываемся на collection trades только на trades, которые имеют robo_name name, позволяя робтам легко друг-друга различать

### Идеи по архитектуре

Все события представлены в виде объектов, которые подаются роботу, после обработки робот может сменить внутренне состояние и выдать желаемые действия в виде списка ордеров. Если мы в разное время подадим роботу одинаковую последовательность событий, то действия его будут идентичными. Логируем все входящий события, по ним возможно 100% восстановить внутренее состояние робота и его действия, проблема тестирования в этом случае очень упрощается.

### Analyzer

Читает лог торгов и на основе них генерируется внутреннее состояние торговых роботов и их действия и сохраняет в базу данных для дальнейшего анализа
