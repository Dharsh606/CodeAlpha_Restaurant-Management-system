from flask import Flask, request, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
db = SQLAlchemy(app)

# ----------- MODELS -----------
class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True)
    seats = db.Column(db.Integer)
    is_reserved = db.Column(db.Boolean, default=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'))
    quantity = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'))
    customer_name = db.Column(db.String(100))
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ----------- ROUTES -----------

@app.route('/')
def home():
    tables = Table.query.all()
    menu = MenuItem.query.all()
    return render_template_string("""
    <h1>Restaurant System</h1>
    <h2>Available Tables</h2>
    {% for t in tables %}
        <p>Table {{ t.number }} - Seats: {{ t.seats }} - {% if t.is_reserved %} Reserved {% else %} Free {% endif %}</p>
    {% endfor %}
    
    <h2>Menu</h2>
    {% for item in menu %}
        <p>{{ item.name }} - ₹{{ item.price }} (Stock: {{ item.stock }})</p>
    {% endfor %}
    
    <a href="{{ url_for('reserve_table') }}">Reserve a Table</a> |
    <a href="{{ url_for('place_order') }}">Place Order</a> |
    <a href="{{ url_for('sales_report') }}">Sales Report</a>
    """, tables=tables, menu=menu)

# ----------- Table Reservation -----------
@app.route('/reserve', methods=['GET', 'POST'])
def reserve_table():
    if request.method == 'POST':
        table_id = int(request.form['table_id'])
        name = request.form['name']
        table = Table.query.get(table_id)
        if table and not table.is_reserved:
            table.is_reserved = True
            db.session.add(Reservation(table_id=table.id, customer_name=name))
            db.session.commit()
            flash("Table reserved.")
        else:
            flash("Table not available.")
        return redirect(url_for('home'))

    tables = Table.query.filter_by(is_reserved=False).all()
    return render_template_string("""
    <h2>Reserve Table</h2>
    <form method="POST">
        Name: <input name="name" required><br>
        Table: 
        <select name="table_id">
            {% for t in tables %}
                <option value="{{ t.id }}">Table {{ t.number }} ({{ t.seats }} seats)</option>
            {% endfor %}
        </select><br>
        <button type="submit">Reserve</button>
    </form>
    <a href="{{ url_for('home') }}">Back</a>
    """, tables=tables)

# ----------- Place Order -----------
@app.route('/order', methods=['GET', 'POST'])
def place_order():
    if request.method == 'POST':
        table_id = int(request.form['table_id'])
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])

        item = MenuItem.query.get(item_id)
        table = Table.query.get(table_id)

        if not table or table.is_reserved == False:
            flash("Invalid or unreserved table.")
        elif item.stock < quantity:
            flash("Not enough stock.")
        else:
            item.stock -= quantity
            db.session.add(Order(table_id=table_id, item_id=item_id, quantity=quantity))
            db.session.commit()
            flash("Order placed.")
        return redirect(url_for('home'))

    tables = Table.query.filter_by(is_reserved=True).all()
    menu = MenuItem.query.filter(MenuItem.stock > 0).all()
    return render_template_string("""
    <h2>Place Order</h2>
    <form method="POST">
        Table: 
        <select name="table_id">
            {% for t in tables %}
                <option value="{{ t.id }}">Table {{ t.number }}</option>
            {% endfor %}
        </select><br>
        Item: 
        <select name="item_id">
            {% for m in menu %}
                <option value="{{ m.id }}">{{ m.name }} (₹{{ m.price }})</option>
            {% endfor %}
        </select><br>
        Quantity: <input type="number" name="quantity" min="1"><br>
        <button type="submit">Order</button>
    </form>
    <a href="{{ url_for('home') }}">Back</a>
    """, tables=tables, menu=menu)

# ----------- Sales Report -----------
@app.route('/report')
def sales_report():
    orders = db.session.query(
        MenuItem.name,
        db.func.sum(Order.quantity),
        db.func.sum(Order.quantity * MenuItem.price)
    ).join(MenuItem).group_by(MenuItem.id).all()

    return render_template_string("""
    <h2>Sales Report</h2>
    <table border="1">
        <tr><th>Item</th><th>Qty Sold</th><th>Total ₹</th></tr>
        {% for name, qty, total in orders %}
            <tr><td>{{ name }}</td><td>{{ qty }}</td><td>{{ total }}</td></tr>
        {% endfor %}
    </table>
    <a href="{{ url_for('home') }}">Back</a>
    """ , orders=orders)

# ----------- DB Initialization -----------
def init_db():
    db.create_all()
    if not Table.query.first():
        db.session.add_all([
            Table(number=1, seats=4),
            Table(number=2, seats=6),
            Table(number=3, seats=2),
        ])
    if not MenuItem.query.first():
        db.session.add_all([
            MenuItem(name="Pizza", price=250, stock=20),
            MenuItem(name="Burger", price=150, stock=30),
            MenuItem(name="Pasta", price=200, stock=25),
        ])
    db.session.commit()

# ----------- Run App -----------
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
