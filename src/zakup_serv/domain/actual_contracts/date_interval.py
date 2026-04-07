

class DateInterval:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date


    def __repr__(self):
        return f"{self.__class__.__name__}(start_date={self.start_date}, end_date={self.end_date})"