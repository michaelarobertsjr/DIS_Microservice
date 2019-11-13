from flask import Flask, request, render_template, make_response
import sqlalchemy as db
import pymysql
import jwt
import http
import json
import requests

app = Flask(__name__)

app.config['TRADIER_BEARER'] = ''
app.config['SECRET'] = ''
app.config['DB_HOST'] = ''
app.config['DB_USER'] = ''
app.config['DB_PASS'] = ''
app.config['DB_NAME'] = ''

engine = db.create_engine('mysql+pymysql://' + app.config['DB_USER'] + ':' + app.config['DB_PASS'] + '@' + app.config['DB_HOST'] + '/' + app.config['DB_NAME'], pool_pre_ping=True)
app.config['DB_CONN'] = engine.connect()

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
    return res

@app.route('/api/buy', methods=['POST'])
def buy():
    auth = request.headers.get('auth')
    quantity = request.headers.get('quantity')

    try:
        decoded = jwt.decode(auth, app.config['SECRET'], algorithm='HS256')
        uid = decoded['uid']
        username = decoded['username']
        email = decoded['email']

        res = requests.get('http://localhost:5001/api/quotes')
        price = json.loads(res.headers['quote'].replace('\'', '\"'))['quotes']['quote']['last']

        sql = 'INSERT INTO buy_sell(b_type, username, t_account, price, quantity) VALUES(\'buy\', \'' + username + '\', \'' + email + '\', \'' + str(price) + '\', \'' + quantity + '\')'
        app.config['DB_CONN'].execute(sql)
        
    except jwt.ExpiredSignatureError:
        print('Expired Token')
    except jwt.DecodeError:
        print('Invalid Token')
    return 'Working on it', 200

@app.route('/api/sell', methods=['POST'])
def sell():
    auth = request.headers.get('auth')
    quantity = request.headers.get('quantity')

    try:
        decoded = jwt.decode(auth, app.config['SECRET'], algorithm='HS256')
        uid = decoded['uid']
        username = decoded['username']
        email = decoded['email']

        res = requests.get('http://localhost:5001/api/quotes')
        price = json.loads(res.headers['quote'].replace('\'', '\"'))['quotes']['quote']['last']

        sql = 'INSERT INTO buy_sell(b_type, username, t_account, price, quantity) VALUES(\'sell\', \'' + username + '\', \'' + email + '\', \'' + str(price) + '\', \'' + quantity + '\')'
        app.config['DB_CONN'].execute(sql)
        
    except jwt.ExpiredSignatureError:
        print('Expired Token')
    except jwt.DecodeError:
        print('Invalid Token')
    return 'Working on it', 200

@app.route('/api/transactions', methods=['GET'])
def transactions():
    auth = request.headers.get('auth')
    transactions = json.loads('{}')
    try:
        decoded = jwt.decode(auth, app.config['SECRET'], algorithm='HS256')
        account = decoded['email']
        if account == 'admin@obs.com':

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

    except jwt.ExpiredSignatureError:
        print('Expired Token')
    except jwt.DecodeError:
        print('Invalid Token')

    return transactions, 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)