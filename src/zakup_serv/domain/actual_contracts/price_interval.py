

class PriceInterval:
    def __init__(self, min_price, max_price):
        self.min_price = min_price
        self.max_price = max_price

    def __repr__(self):
        return f"{self.__class__.__name__}(min_price={self.min_price}, max_price={self.max_price})"