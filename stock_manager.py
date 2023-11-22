from datetime import datetime, timedelta
import pandas as pd
import requests
from io import StringIO
from os import getenv


class Stock:
    def __init__(self, stock_range='1D', ticker='AAPL', api_key=getenv('STOCK_API_KEY')):

        self.stock_range = stock_range
        self.ticker = ticker
        self.api_key = api_key

        if self.ticker is None:
            self.ticker = 'AAPL'
        if self.stock_range is None:
            self.stock_range = '1D'

        self.first_trade_day = None
        self.recent_data = None
        self.interval = None
        self.stocks_df = None
        self.last_trade_day = None

        self.time_range_data = self.time_range()
        self.time_range_min = self[0]
        self.time_range_func = self[1]

        self.get_recent_data()

    def __getitem__(self, index: int):
        return self.time_range_data[index]

    def time_range(self):
        # create df
        if self.stock_range == 'YTD':
            stock_data = [None,  # placeholder
                          'TIME_SERIES_DAILY']
        elif 'Y' in self.stock_range:
            y_amount = int(self.stock_range.replace('Y', ''))

            stock_data = [timedelta(days=(365 * y_amount)),
                          'TIME_SERIES_WEEKLY_ADJUSTED']

        elif 'M' in self.stock_range:
            m_amount = int(self.stock_range.replace('M', ''))

            stock_data = [timedelta(days=(31 * m_amount)),
                          'TIME_SERIES_WEEKLY_ADJUSTED']

        elif 'D' in self.stock_range:
            self.interval = '5min'
            d_amount = int(self.stock_range.replace('D', ''))
            stock_data = [timedelta(days=d_amount),
                          'TIME_SERIES_INTRADAY']
        elif self.stock_range == 'All':
            stock_data = [None,  # placeholder
                          'TIME_SERIES_WEEKLY_ADJUSTED']
        else:

            self.interval = '5min'
            stock_data = [timedelta(days=1),
                          'TIME_SERIES_INTRADAY']

        self.parse_df(stock_func=stock_data[1])
        self.last_trade_day = self.stocks_df.date[0]
        self.first_trade_day = self.stocks_df.date.iloc[-1]

        if self.stock_range == 'YTD':
            stock_data[0] = self.last_trade_day - datetime(year=self.last_trade_day.year, month=1, day=1)
        if self.stock_range == 'All':
            stock_data[0] = self.last_trade_day - self.first_trade_day

        return stock_data

    @property
    def xaxis_range(self):
        if self.time_range_func != 'TIME_SERIES_INTRADAY':
            return [(self.last_trade_day - self.time_range_min), self.last_trade_day]

    @property
    def yaxis_range(self):
        if self.time_range_func != 'TIME_SERIES_INTRADAY':
            return [  # min/max recent data            # extra margin
                float(self.recent_data['close'].min() - (self.recent_data['close'].min() / 20)),
                float(self.recent_data['close'].max() + (self.recent_data['close'].max() / 20))
            ]

    def parse_df(self, stock_func):
        df_url = f"https://www.alphavantage.co/query.csv?" \
                 f"function={stock_func}&symbol={self.ticker}" \
                 f"&apikey={self.api_key}&datatype=csv&outputsize=full" \
                 f"{'&interval=' + self.interval if self.interval else ''}"
        self.stocks_df = pd.read_csv(StringIO(requests.get(df_url).text))

        # parse df
        if stock_func == 'TIME_SERIES_WEEKLY_ADJUSTED':
            self.stocks_df = self.stocks_df.rename(columns={"timestamp": "date",
                                                            "close": "unadjusted close",
                                                            'adjusted close': 'close'})
        else:
            self.stocks_df = self.stocks_df.rename(columns={"timestamp": "date"})
        self.stocks_df['date'] = pd.to_datetime(self.stocks_df['date'])

        return self.stocks_df

    # def parse_df(self, stock_func):
    #
    #     df_url = (f"https://api.polygon.io/v2/aggs/ticker/AAPL/"
    #               f"range/1/minute/"
    #               f"1970-01-01/{date.today().strftime("%Y-%m-%d")}"
    #               f"?adjusted=true&sort=desc&apiKey=Bp8eNb424HkubDccEx8mhzsyqKqmc1Td")
    #     print(str(requests.get(df_url).json()))
    #     # self.stocks_df = pd.read_json(str(requests.get(df_url).json()['results']))
    #     # print(self.stocks_df)
    #
    #     # parse df
    #     if stock_func == 'TIME_SERIES_WEEKLY_ADJUSTED':
    #         self.stocks_df = self.stocks_df.rename(columns={"timestamp": "date",
    #                                                         "close": "unadjusted close",
    #                                                         'adjusted close': 'close'})
    #     else:
    #         self.stocks_df = self.stocks_df.rename(columns={"timestamp": "date"})
    #     self.stocks_df['date'] = pd.to_datetime(self.stocks_df['date'])
    #
    #     return self.stocks_df

    def get_recent_data(self):
        # get recent data

        self.recent_data = self.stocks_df.loc[
            (self.stocks_df['date'] > (self.last_trade_day - self.time_range_min))]

        if self.time_range_func == 'TIME_SERIES_INTRADAY':
            self.stocks_df = self.recent_data


stock = Stock()
stock.parse_df('hello')
