# engine/macross.py


import pandas as pd 
import numpy as np 
import mplfinance as mpf 
import matplotlib
import matplotlib.pyplot as plt 
import matplotlib.patches as patches
import yfinance as yf 
from utils.normalize_ohlc import to_unix_timestamp
from utils.get_data import get_ohlc
import time  

import requests


matplotlib.use("Agg")


class MaCross:

	def __init__(
			self,
			symbol, 
			interval,
			ma_fast: int=21,
			ma_slow: int=50,
			ma_type: str="sma",
			backtest=False,
			live_trade=False,
			**kwargs
		):

		self.symbol = symbol
		self.interval = interval
		self.ma_fast = ma_fast
		self.ma_slow = ma_slow
		self.ma_type = ma_type
		self.backtest = backtest


		self.kwargs = kwargs



	def prepare_df(self):
		# Determine default lookback
		interval_minutes = {
			"1m": 1, "5m": 5, "15m": 15,
			"30m": 30, "1h": 60, "4h": 240,
			"1d": 1440,
		}[self.interval]

		default_minutes = 300 * interval_minutes
		start_mask = pd.Timestamp.now() - pd.Timedelta(minutes=default_minutes)

		start = to_unix_timestamp(self.kwargs.get("start", start_mask))
		end = to_unix_timestamp(self.kwargs.get("end", int(time.time())))

		# Safety: swap if reversed
		if start and end and start > end:
			start, end = end, start

		# Fetch OHLC data
		self.df = get_ohlc(symbol=self.symbol, timeframe=self.interval, from_date=start, to_date=end)
		# self.df
		# print(self.df)
		self.df.columns = [col.lower() for col in self.df.columns]
		if "datetime" in self.df.columns:

			self.df["datetime"] = pd.to_datetime(self.df["datetime"], unit="s", utc=True)
			self.df.set_index("datetime", inplace=True)



	def add_indicator(self):

		if self.ma_type.lower() == "sma":
			self.df[f"ma{self.ma_fast}"] = self.df["close"].rolling(window=self.ma_fast).mean()
			self.df[f"ma{self.ma_slow}"] = self.df["close"].rolling(window=self.ma_slow).mean()

		elif self.ma_type.lower() == "ema":
			self.df[f"ma{self.ma_fast}"] = self.df["close"].ewm(span=self.ma_fast, adjust=False).mean()
			self.df[f"ma{self.ma_slow}"] = self.df["close"].ewm(span=self.ma_slow, adjust=False).mean()


	def add_signal(self):
		self.df['signal'] = np.select(
			[
				(
					(self.df[f"ma{self.ma_fast}"] > self.df[f"ma{self.ma_slow}"]) &
					(self.df[f"ma{self.ma_fast}"].shift(1) <= self.df[f"ma{self.ma_slow}"].shift(1))
				),
				(
					(self.df[f"ma{self.ma_fast}"] < self.df[f"ma{self.ma_slow}"]) &
					(self.df[f"ma{self.ma_fast}"].shift(1) >= self.df[f"ma{self.ma_slow}"].shift(1))
				)
			],
			[1, -1],
			default=0,
		)



	def add_trade_id(self):
		self.df["trade_id"] = (self.df["signal"] != 0).astype(int).cumsum().ffill()

	def add_sl_tp_percent(self):
		sl: int = self.kwargs.get("sl", 0.003)
		tp: int = self.kwargs.get("tp", 0.006)

		self.df["sl_price"] = np.select(
			[self.df["signal"] == 1, self.df["signal"] == -1],
			[self.df["close"] * (1 - sl), self.df["close"] * (1 + sl)],
			default=np.nan,
		)

		self.df["tp_price"] = np.select(
			[self.df["signal"] == 1, self.df["signal"] == -1],
			[self.df["close"] * (1 + tp), self.df["close"] * (1 - tp)],
			default=np.nan,
		)


		self.df["sl_price"] = self.df.groupby("trade_id")["sl_price"].ffill()
		self.df["tp_price"] = self.df.groupby("trade_id")["tp_price"].ffill()


	def add_trade_index_price(self):

		entries = self.df.index[self.df["signal"] != 0]

		self.df["entry_index"] = np.nan
		self.df["entry_price"] = np.nan
		self.df["exit_index"] = np.nan
		self.df["exit_price"] = np.nan

		for entry_idx in entries:
			entry_price = self.df.at[entry_idx, "close"]
			signal = self.df.at[entry_idx, "signal"]
			sl = self.df.at[entry_idx, "sl_price"]
			tp = self.df.at[entry_idx, "tp_price"]

			trade_slice = self.df.loc[entry_idx:]
			exit_bar = None	

			for j, row in trade_slice.iterrows():
				if signal == 1 and (row['low'] <= sl or row['high'] >= tp):
					exit_bar = j
					break 

				elif signal == -1 and (row['high'] >= sl or row['low'] <= tp):
					exit_bar = j 
					break 

			if exit_bar is None:
				exit_bar = trade_slice.index[-1]

			self.df.at[entry_idx, "entry_index"] = self.df.index.get_loc(entry_idx)
			self.df.at[entry_idx, "entry_price"] = entry_price
			self.df.at[entry_idx, "exit_index"] = self.df.index.get_loc(exit_bar)
			self.df.at[entry_idx, "exit_price"] = self.df.at[exit_bar, "close"]


	def create_trades_df(self):

		self.trades_df = (
			self.df.groupby("trade_id", dropna=True)
			.agg(
				entry_index=("entry_index", "first"),
				exit_index=("exit_index", "first"),
				entry_price=("entry_price", "first"),
				exit_price=("exit_price", "first"),
				sl_price=("sl_price", "first"),
				tp_price=("tp_price", "first"),
				direction=("signal", "first"),
			)
			.reset_index(drop=True)
		)

		self.trades_df = self.trades_df[~self.trades_df["entry_index"].isna()]
		return self.trades_df


	def alert_fig(self):

		fig, ax = plt.subplots(figsize=self.kwargs.get("figsize", (30, 10)))

		# ma + markers
		ma_fast_ind = mpf.make_addplot(
			data = self.df[f"ma{self.ma_fast}"],
			color = self.kwargs.get("ma_fast_color", "red"),
			width = self.kwargs.get("ma_fast_width", 1),
			ax=ax,
		)
		ma_slow_ind = mpf.make_addplot(
			data = self.df[f"ma{self.ma_slow}"],
			color = self.kwargs.get("ma_slow_color", "blue"),
			width = self.kwargs.get("ma_slow_width", 1),
			ax=ax,
		)

		marker_long = mpf.make_addplot(
			data = self.df['close'].where(self.df['signal'] == 1) * 0.996,
			type ='scatter',
			markersize=80,
			marker='^',
			color=self.kwargs.get("marker_long_color", "green"),
			ax=ax,
		)
		marker_short = mpf.make_addplot(
			data = self.df['close'].where(self.df['signal'] == -1) * 1.004,
			type ='scatter',
			markersize=80,
			marker='v',
			color=self.kwargs.get("marker_short_color", "red"),
			ax=ax,
		)


		apds = [ma_fast_ind, ma_slow_ind, marker_long, marker_short]

		# styling
		my_marketcolors = mpf.make_marketcolors(
			up=self.kwargs.get("bull_canlde_color", 'green'),
			down=self.kwargs.get("bear_canlde_color", 'red'),
			edge=self.kwargs.get("edge_candle_color", 'inherit'),
			wick=self.kwargs.get("wick_candle_color", 'inherit'),
			volume=self.kwargs.get("volume_color", 'inherit')
		)
		my_style = mpf.make_mpf_style(
			base_mpf_style=self.kwargs.get("base_mpf_style", "classic"),
			marketcolors=my_marketcolors,
		#     facecolor=self.kwargs.get("facecolor", '#a1c3f0'), #! set this wiht ax is better
		#     edgecolor=self.kwargs.get("edgecolor", 'white'),
		#     gridcolor=self.kwargs.get("gridcolor", 'white'),
		#     gridstyle=self.kwargs.get("gridstyle", "-")
		)


		mpf.plot(
			self.df,
			type="candle",
			style=my_style,
			addplot=apds,
			volume=False,
			ax=ax,
		)

		ax.set_facecolor(self.kwargs.get("background_color", "#a1c3f0"))
		# Edgecolor: around the axes
		for spine in ax.spines.values():
			spine.set_edgecolor(self.kwargs.get("edge_color", "white"))

		if self.kwargs.get("draw_grid", False) == True:
			ax.grid(True,
				color='white',
				linestyle='-',
				linewidth=0.8
			)
		elif self.kwargs.get("draw_grid", False) == False:
			ax.grid(False)

		ax.tick_params(axis='both', which='major', labelsize=self.kwargs.get("labels_font_size", 4))


		# position box
		sl: int = self.kwargs.get("sl", 0.003)
		tp: int = self.kwargs.get("tp", 0.006)

		if sl is not None and tp is not None:

			for _, row in self.df[self.df['signal'] != 0].iterrows():
				x0, y0 = row['entry_index'], row['entry_price']
				x1, y1 = row['exit_index'], row['exit_price']
				if np.isnan(x1) or np.isnan(y1):
					continue

				width = x1 - x0
				sl, tp = row['sl_price'], row['tp_price']

				height_green = abs(tp - y0)
				height_red = abs(y0 - sl)

				if row['signal'] == 1:  # Long
					ax.add_patch(patches.Rectangle(
						(x0, y0), width, height_green,
						color=self.kwargs.get("position_box_long_tp_color", "green"),
						alpha=self.kwargs.get("position_box_alpha", 0.3)
					))
					ax.add_patch(patches.Rectangle(
						(x0, y0), width, -height_red,
						color=self.kwargs.get("position_box_long_sl_color", "red"),
						alpha=self.kwargs.get("position_box_alpha", 0.3)
					))
				elif row['signal'] == -1:  # Short
					ax.add_patch(patches.Rectangle(
						(x0, y0), width, -height_green,
						color=self.kwargs.get("position_box_short_tp_color", "green"),
						alpha=self.kwargs.get("position_box_alpha", 0.3)
					))
					ax.add_patch(patches.Rectangle(
						(x0, y0), width, height_red,
						color=self.kwargs.get("position_box_short_sl_color", "red"),
						alpha=self.kwargs.get("position_box_alpha", 0.3)
					))


		lines = ax.get_lines() 
		ax.legend(
			[lines[0], lines[1]],  
			["MA Fast", "MA Slow"],   # the labels you want
			loc="upper left"
		)

		plt.tight_layout()
		return fig




	def backtest_fig(self):
		pass


	def run_perc(self):
		self.prepare_df()
		self.add_indicator()
		self.add_signal()
		self.add_trade_id()
		self.add_sl_tp_percent()
		self.add_trade_index_price()
		return self  # enable chaining



# testing
# test1 = MaCross(symbol="eurusd=x", interval="15m", ma_fast=9, ma_slow=18, ma_type="ema")

# print(test1.run_perc().create_trades_df())


# test_ohlc = MaCross("EURUSD", "15m").prepare_df()


# testing alert fig
fig = MaCross(symbol="EURUSD", interval="4h", ma_fast=9, ma_slow=18, ma_type="sma").run_perc().alert_fig()

fig.savefig("engine/user_charts/alert_chart.png")