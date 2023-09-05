__all__ = ["AgentTask"]

import a107, dateutil, datetime


class AgentTask(a107.AutoClass):
    def calculate_nexttime(self):
        a, b = float("inf"), float("inf")
        if self.time_of_day:
            # a contains today's date with time time_of_day
            tmp = dateutil.parser.parse(self.time_of_day)
            if tmp < datetime.datetime.now():
                # makes it tomorrow only if time_of_day is past
                tmp += datetime.timedelta(days=1)
            a = tmp.timestamp()
        if self.interval is not None:
            b = self.lasttime + self.interval
        self.nexttime = min(a, b)
