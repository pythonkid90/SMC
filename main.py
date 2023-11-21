from secrets import token_hex
from os import getenv

import requests
from sqlalchemy.exc import NoResultFound
import plotly.express as px

from flask import Flask, render_template, request, redirect, url_for, flash, stream_template
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import check_password_hash, generate_password_hash

from stock_manager import Stock
from tables import init_tables

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = getenv('DB_URI', "sqlite:///stocks.db")
app.secret_key = token_hex()

db = SQLAlchemy(app)
User, StockData = init_tables(db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def create_plot():
    if request.args.get('ticker'):
        stock = Stock(stock_range=request.args.get('time-range'), ticker=request.args.get('ticker'))

        plot = px.line(stock.stocks_df, x='date', y='close').update_layout(yaxis_range=stock.yaxis_range,
                                                                           xaxis_range=stock.xaxis_range)

        with open('templates/graph.html', 'w') as graph_HTML:
            graph_HTML.write(plot.to_html())

        ticker = request.args.get('ticker') if request.args.get('ticker') else 'AAPL'
        time_range = request.args.get('time-range') if request.args.get('time-range') else '1D'
    else:
        ticker, time_range = None, None

    return ticker, time_range


def get_stock_data():
    stocks = []
    stock_amount = 0
    current_user.money = current_user.cash
    for user_stock in StockData.query.all():
        if user_stock.user_username == current_user.username:
            # user = db.session.execute(db.select(User).filter_by(username=current_user.username)).scalar_one()

            cur_price = float(requests.get(f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE'
                                           f'&symbol={user_stock.stock}'
                                           f'&apikey={getenv('STOCK_API_KEY')}').json()['Global Quote']['05. price'])
            price_change = float(cur_price) - float(user_stock.start_price)

            stock_data = {'ticker': user_stock.stock,
                          'shares': user_stock.shares,
                          'start_price': user_stock.start_price,
                          'cur_price': cur_price,
                          'price_change': price_change,
                          'price_change_percent': price_change / user_stock.start_price * 100,
                          'earnings': price_change * int(user_stock.shares)}
            stocks.append(stock_data)

            stock_amount += (cur_price * int(user_stock.shares))

    current_user.money = current_user.money + stock_amount
    return stocks, stock_amount


with app.app_context():
    # db.drop_all()
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/dashboard')
@login_required
def dashboard():
    # # Create Plot # #
    ticker, time_range = create_plot()

    stocks, stock_amount = get_stock_data()

    return stream_template('dashboard.html', ticker=ticker, cur_time_range=time_range, stocks=stocks, stock_amount=stock_amount)


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            user = db.session.execute(db.select(User).filter_by(username=request.form.get('username'))).scalar_one()
            if check_password_hash(user.password, request.form.get('password')):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Wrong password. Please try again.')
        except NoResultFound:
            flash('Username does not exist. Please try again.')
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form.get('username'),  # noqa
                    password=generate_password_hash(request.form.get('password')), money=100000, cash=100000)  # noqa
        if not User.query.filter_by(username=user.username).scalar():
            db.session.add(user)
            db.session.commit()
            login_user(user)
        else:
            flash('Username in database. Login instead.')
            return redirect(url_for('login'))
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    if request.method == 'POST':
        start_price = float(requests.get(f'https://www.alphavantage.co/query?'
                                   f'function=GLOBAL_QUOTE&'
                                   f'symbol={request.form.get('ticker')}&'
                                   f'apikey={getenv('STOCK_API_KEY')}').json()['Global Quote']['05. price'])
        if start_price * int(request.form.get('shares')) > current_user.cash:
            flash('You cannot afford to buy that many shares!')
            return redirect(url_for('buy'))

        stock_in_db = db.session.execute(db.select(StockData).filter_by(stock=request.form.get('ticker'))).scalar_one_or_none()
        if stock_in_db:
            stock_in_db.shares += int(request.form.get('shares'))
        else:
            db.session.add(StockData(stock=request.form.get('ticker'),
                                     shares=request.form.get('shares'),
                                     start_price=start_price,
                                     user=current_user
                                     ))
        # user = db.session.execute(db.select(User).filter_by(username=current_user.username)).scalar_one()
        current_user.cash -= start_price * int(request.form.get('shares'))
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('buy.html')


@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    if request.method == 'POST':
        stock = db.session.execute(db.select(StockData).filter_by(user_username=current_user.username, stock=request.form.get('ticker'))).scalar_one()
        # user = db.session.execute(db.select(User).filter_by(username=current_user.username)).scalar_one()
        if int(request.form.get('shares')) > stock.shares:
            flash('You cannot sell that many shares!')
            return redirect(url_for('sell'))
        elif int(request.form.get('shares')) == stock.shares:
            db.session.delete(stock)
        stock.shares -= int(request.form.get('shares'))
        current_user.cash += float(requests.get(f'https://www.alphavantage.co/query?'
                                   f'function=GLOBAL_QUOTE&'
                                   f'symbol={request.form.get('ticker')}&'
                                   f'apikey={getenv('STOCK_API_KEY')}').json()['Global Quote']['05. price']) * int(request.form.get('shares'))
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('buy.html')


# if __name__ == '__main__':
#     app.run(debug=True)