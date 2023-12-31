from flask_login import UserMixin


def init_tables(db):
    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String, unique=True, nullable=False)
        password = db.Column(db.String, nullable=False)
        cash = db.Column(db.Float, nullable=False)
        money = db.Column(db.Float, nullable=False)
        starting_money = db.Column(db.Float, nullable=False)
        stocks = db.relationship('StockData', backref='user')


    class StockData(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        stock = db.Column(db.String, nullable=False)
        shares = db.Column(db.Float, nullable=False)
        start_price = db.Column(db.Float, nullable=False)
        user_username = db.Column(db.String, db.ForeignKey('user.username'))

    return User, StockData
