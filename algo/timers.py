class TimerIRQ:
    def __init__(self, timer_type):
        self.timer_type = timer_type
        self.subscribers = []


class Timers:
    def __init__(self):
        self.timers = {}

    def update(self, event):
        #print("inside timers ", event)
        if event.type in self.timers:
            for callback in self.timers[event.type].subscribers:
                yield from callback()

    def subscribe(self, timer_type, callback):
        if not timer_type in self.timers:
            self.timers[timer_type] = TimerIRQ(timer_type)

        if not callback in self.timers[timer_type].subscribers:
            self.timers[timer_type].subscribers.append(callback)

        return self.timers[timer_type]
