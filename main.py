from secrets import token_hex
from os import getenv

import requests
from sqlalchemy.exc import NoResultFound
import plotly.express as px

from flask import Flask, render_template, request, redirect, url_for, flash
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
        price = int(stock.stocks_df.close[0])
    else:
        ticker, time_range, price = None, None, None

    return ticker, time_range, price


def get_cur_price(ticker):
    if not getenv('POLYGON_API_KEY'):
        return float(requests.get(f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE'
                                  f'&symbol={ticker}'
                                  f'&apikey={getenv('STOCK_API_KEY')}').json()['Global Quote']['05. price'])
    else:
        stock_data = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{ticker}"
                                  f"/prev?adjusted=true&apiKey={getenv('POLYGON_API_KEY')}"
                                  ).json()
        return float(stock_data['results'][0]['c'])


def get_stock_data():
    stocks = []
    stock_amount = 0
    current_user.money = current_user.cash
    for user_stock in StockData.query.all():
        if user_stock.user_username == current_user.username:
            cur_price = get_cur_price(user_stock.stock)

            price_change = float(cur_price) - float(user_stock.start_price)

            stock_data = {'ticker': user_stock.stock,
                          'shares': round(user_stock.shares, 2),
                          'start_price': user_stock.start_price,
                          'cur_price': cur_price,
                          'price_change': round(price_change, 2),
                          'price_change_percent': round(price_change / user_stock.start_price * 100, 2),
                          'earnings': round(price_change * float(user_stock.shares), 2),
                          'stock_value': round(cur_price * float(user_stock.shares), 2)}
            stocks.append(stock_data)

            # total_earnings += price_change * float(user_stock.shares)
            stock_amount += round(cur_price * float(user_stock.shares), 2)

    # user = db.session.execute(db.select(User).filter_by(username=current_user.username)).scalar_one()
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
    ticker, time_range, price = create_plot()

    stocks, stock_amount = get_stock_data()

    return render_template('dashboard.html', ticker=ticker, cur_time_range=time_range, stocks=stocks,
                           stock_amount=stock_amount, stock_price=price, round=round, float=float)


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
                if request.args.get('next'):
                    return redirect(request.args.get('next'))
                else:
                    return redirect(url_for('dashboard'))

            else:
                flash('Wrong password. Please try again.')
        except NoResultFound:
            flash('Username does not exist. Please try again.')


    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form.get('username'),  # noqa
                    password=generate_password_hash(request.form.get('password')),
                    money=float(request.form.get('starting_money')),
                    cash=float(request.form.get('starting_money')),
                    starting_money=float(request.form.get('starting_money')))

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
        start_price = get_cur_price(request.form.get('ticker'))
        if start_price * float(request.form.get('shares')) > current_user.cash:
            flash('You cannot afford to buy that many shares!')
            return redirect(url_for('buy'))

        stocks_in_db = db.session.execute(
            db.select(StockData).filter_by(stock=request.form.get('ticker'))).scalars().all()

        if stocks_in_db:
            for stock in stocks_in_db:
                if stock.start_price == start_price:
                    stock.shares += float(request.form.get('shares'))
        else:
            db.session.add(StockData(stock=request.form.get('ticker').upper(),
                                     shares=request.form.get('shares'),
                                     start_price=start_price,
                                     user=current_user
                                     ))
        current_user.cash -= round(start_price * float(request.form.get('shares')), 2)
        db.session.commit()
        if request.args.get('next'):
            return redirect(request.args.get('next'))
        return redirect(url_for('dashboard'))
    return render_template('buy.html')


@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    if request.method == 'POST':
        stocks = db.session.execute(db.select(StockData).filter_by(user_username=current_user.username,
                                                                   stock=request.form.get('ticker').upper())
                                    ).scalars()

        for stock in stocks:

            if round(float(request.form.get('shares')), 2) == round(stock.shares, 2):
                shares_to_sell = True

                db.session.delete(stock)
                break
            elif stock.shares == 0:
                shares_to_sell = True
                db.session.delete(stock)
                continue
            elif float(request.form.get('shares')) > round(stock.shares, 2):
                shares_to_sell = False
                continue
            else:
                shares_to_sell = True
                stock.shares -= float(request.form.get('shares'))

        if shares_to_sell:  # noqa
            current_user.cash += get_cur_price(request.form.get('ticker')) * float(request.form.get('shares'))
        else:
            flash('You cannot sell that many shares!')
            return redirect(url_for('sell'))

        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('buy.html')


@app.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    if request.method == "POST":
        if check_password_hash(current_user.password, request.form.get('password')):
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
        else:
            flash('Wrong password.')
        return redirect(url_for('home'))

    return render_template('delete.html')



# if __name__ == '__main__':
#     app.run(debug=True)
