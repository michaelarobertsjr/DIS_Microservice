from flask import Flask, request, render_template, make_response
import sqlalchemy as db
import pymysql
import jwt
import http
import json
import requests

app = Flask(__name__)

app.config['TRADIER_BEARER'] = 'uhzCQ8Lzm5Tx35faBndmsYmQgE4d'
app.config['SECRET'] = 'XCAP05H6LoKvbRRa/QkqLNMI7cOHguaRyHzyg7n5qEkGjQmtBhz4SzYh4Fqwjyi3KJHlSXKPwVu2+bXr6CtpgQ=='
app.config['DB_HOST'] = ''
app.config['DB_USER'] = ''
app.config['DB_PASS'] = ''
app.config['DB_NAME'] = ''

engine = db.create_engine('mysql+pymysql://' + app.config['DB_USER'] + ':' + app.config['DB_PASS'] + '@' + app.config['DB_HOST'] + '/' + app.config['DB_NAME'], pool_pre_ping=True)
app.config['DB_CONN'] = engine.connect()

def authenticate(auth):
    output = {
        'uid' : '',
        'username' : '',
        'email' : ''
    }
    try:
        decoded = jwt.decode(auth, app.config['SECRET'], algorithm='HS256')

        output['uid'] = decoded['uid']
        output['username'] = decoded['username']
        output['email'] = decoded['email']
        
    except jwt.ExpiredSignatureError:
        print('Expired Token')
    except jwt.DecodeError:
        print('Invalid Token')
    return output

def save_to_db(b_type, name, acc, price, amt):

    if name != '' and acc != '' and float(price) > 0 and int(amt) > 0:
        sql = 'INSERT INTO buy_sell(b_type, username, t_account, price, quantity) VALUES(\'' + b_type + '\', \'' + name + '\', \'' + acc + '\', \'' + str(price) + '\', \'' + str(amt) + '\')'
        app.config['DB_CONN'].execute(sql)
        return 1
    else:
        return 0

def form_buy_sell_response(b_type, name, acc, price, amt):

    value = float(price) * int(amt)
    transaction = json.loads('{}')

    if b_type == 'BUY':
        output_str = "{\"TransactionType\" : \"BUY\", \"User\" : \"" + name + "\", \"Account\" : \"Savings Account\", \"Price\" : " + str(price) + ", \"Quantity\" : " + str(amt) + ", \"CostToUser\" : " + str(value)+ "}"
    elif b_type == 'SELL':
        output_str = "{\"TransactionType\" : \"SELL\", \"User\" : \"" + name + "\", \"Account\" : \"Savings Account\", \"Price\" : " + str(price) + ", \"Quantity\" : " + str(amt) + ", \"CostToUser\" : " + str(value)+ "}"
    
    try:
        transaction = json.loads(output_str)
    except json.JSONDecodeError:
        print('Error while forming JSON response for transaction')
    return transaction

#utilize get requests for quotes (using auth header) and transcations (using auth header with admin user)
#and post requests for buy and sell, returning data for the sale made/failed
@app.route('/api/quotes', methods=["GET"])
def quotes():
    conn = http.client.HTTPSConnection('sandbox.tradier.com', 443, timeout=15)

    headers = {'Accept' : 'application/json', 'Authorization' : 'Bearer ' + app.config['TRADIER_BEARER']}
    quote = json.loads('{}')
    conn.request('GET', '/v1/markets/quotes?symbols=DIS', None, headers)
    try:
        res = conn.getresponse()
        quote = json.loads(res.read().decode('utf-8'))
    except http.client.HTTPException as e:
        print('Quote Request Failed')

    res = make_response()
    res.headers['quote'] = quote

    return quote, 200

@app.route('/api/buy', methods=['POST'])
def buy():
    auth = request.headers.get('auth')
    quantity = request.headers.get('quantity')

    user_data = authenticate(auth)
    
    res = requests.get('http://localhost:5001/api/quotes')
    new_res = res.json()
    price = new_res['quotes']['quote']['last']

    saved = save_to_db('BUY', user_data['username'], user_data['email'], price, quantity)

    buy = form_buy_sell_response('BUY', user_data['username'], user_data['email'], price, quantity)

    return buy, 200

@app.route('/api/sell', methods=['POST'])
def sell():
    auth = request.headers.get('auth')
    quantity = request.headers.get('quantity')

    user_data = authenticate(auth)

    res = requests.get('http://localhost:5001/api/quotes')
    new_res = res.json()
    price = new_res['quotes']['quote']['last']

    saved = save_to_db('SELL', user_data['username'], user_data['email'], price, quantity)

    sell = form_buy_sell_response('BUY', user_data['username'], user_data['email'], price, quantity)
        
    return sell, 200

@app.route('/api/transactions', methods=['GET'])
def transactions():
    auth = request.headers.get('auth')
    transactions = json.loads('{}')

    user_data = authenticate(auth)

    if user_data['email'] == 'admin@obs.com':

        sql = 'SELECT JSON_OBJECT(\'bid\', bid, \'b_type\', b_type, \'username\', username, \'t_account\', t_account, \'price\', price, \'quantity\', quantity) FROM buy_sell'
        query_res = app.config['DB_CONN'].execute(sql).fetchall()
        parsed_query_res = '{\'transactions\': ['

        for entry in query_res:
            parsed_query_res = parsed_query_res + entry[0] + ', '
        parsed_query_res = parsed_query_res[:len(parsed_query_res)-2]
        parsed_query_res += ']}'
        transactions = json.loads(parsed_query_res.replace('\'', '\"'))
    else:
        print('Only the admin may view banking system transactions')

    return transactions, 200

if __name__ == "__main__":


    app.run(debug=True, port=5001)