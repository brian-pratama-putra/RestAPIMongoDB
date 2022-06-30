from flask import Flask, render_template,jsonify,session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity,create_refresh_token
from flask_restful import Resource, request
from flask_pymongo import PyMongo
import json
import hashlib
import datetime
import random
import string


app = Flask(__name__)
app.config['SECRET_KEY'] = '081329047741'
app.config["MONGO_URI"] = "mongodb://localhost:27017/example_data"
mongodb_client = PyMongo(app)
db = mongodb_client.db

app.config['JWT_SECRET_KEY'] = 'BrianPratamaPutra'
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'query_string']
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1) # define the life span of the token
jwt = JWTManager(app) # initialize JWTManager

def responseJSON(status_code, flag, message , result):
    resp = {}
    resp['status_code'] = status_code
    resp['status'] = flag
    resp['message'] = message
    resp['result'] = result
    return resp

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

@app.route("/register",methods=['POST'])
def register():
    try:
        v_raw = json.loads(request.get_data())
        v_first_name = v_raw['v_first_name']
        v_last_name = v_raw['v_last_name']
        v_phone_number = v_raw['v_phone_number']
        v_address = v_raw['v_address']
        v_pin = v_raw['v_pin']

        db.todos.insert_one({'first_name': v_first_name, 
                            'last_name': v_last_name,
                            'phone_number': v_phone_number,
                            'address': v_address,
                            'pin':v_pin})

        return responseJSON(200,'T','Success',[])
    except Exception as error:
        return responseJSON(400,'F',str(error),[])

@app.route("/login", methods=["POST"])
def login():
    try:
        v_raw = json.loads(request.get_data())
        v_phone_number = v_raw['v_phone_number']
        v_pin = v_raw['v_pin']
        user_from_db = db.todos.find_one({"phone_number": v_phone_number,"pin":v_pin})
        if user_from_db:
            if v_pin == user_from_db['pin']:
                access_token = create_access_token(identity=user_from_db['phone_number']) # create jwt token
                refresh_token =create_refresh_token(identity=user_from_db['phone_number'])
                return responseJSON(200,'T','Login berhasil',{'Access Token':access_token,'Refresh Token':refresh_token})
        return responseJSON(401,'F','The username or password is incorrect',[])
    except Exception as error:
        return responseJSON(400,'F',str(error),[])

@app.route("/topup",methods=['POST'])
@jwt_required()
def topup():
    current_user = get_jwt_identity()
    try:
        v_raw = json.loads(request.get_data())
        v_amount = v_raw['v_amount']
        v_phone_number = current_user
        v_id_top_up = get_random_string(10)
        data_saldo = db.saldo.find_one({"phone_number": v_phone_number})
        v_amount_top_up = v_amount
        if data_saldo:
            v_balance_before = data_saldo['amount']
            db.saldo.update_one({'phone_number': v_phone_number}, {"$set": {'amount': v_balance_before+v_amount,'id_top_up':v_id_top_up}})
        else:
            v_balance_before = 0
            db.saldo.insert_one({'phone_number': v_phone_number, 
                            'amount': v_balance_before+v_amount,'id_top_up':v_id_top_up})
        data_saldo = db.saldo.find_one({"phone_number": v_phone_number})
        v_id_topup = data_saldo['id_top_up']
        v_balance_after = v_balance_before + v_amount
        v_created_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        db.history.insert_one({'id_trx':v_id_topup,'status':'SUCCESS',
                            'user':v_phone_number,
                            'transaction_type':'CREDIT',
                            'amount':v_amount,
                            'remarks':'',
                            'balance_before':v_balance_before,
                            'balance_after':v_balance_after,
                            'created_date':v_created_date})
        return responseJSON(200,'T','Success',{'top_up_id':v_id_topup,'amount_top_up':v_amount_top_up,
                                        'balance_before':v_balance_before,'balance_after':v_balance_after,
                                        'created_date':v_created_date})
    except Exception as error:
        db.history.insert_one({'id_trx':v_id_topup,'status':'FAILED',
                            'user':v_phone_number,
                            'transaction_type':'CREDIT',
                            'amount':v_amount,
                            'remarks':str(error),
                            'balance_before':v_balance_before,
                            'balance_after':v_balance_after,
                            'created_date':v_created_date})
        return responseJSON(400,'F',str(error),[])

@app.route("/pay",methods=['POST'])
@jwt_required()
def pay():
    current_user = get_jwt_identity()
    try:
        v_raw = json.loads(request.get_data())
        v_amount = v_raw['v_amount']
        v_remarks = v_raw['v_remarks']
        v_phone_number = current_user
        v_id_payment = get_random_string(10)
        data_saldo = db.saldo.find_one({"phone_number": v_phone_number})
        v_balance_before = data_saldo['amount']
        v_balance_after = (data_saldo['amount'] - v_amount)
        if v_balance_after < 0:
            return responseJSON(400,'F','Balance is not enough',[])
        else:
            db.saldo.update_one({'phone_number': v_phone_number}, {"$set": {'amount': v_balance_after}})
           
            v_created_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db.history.insert_one({'id_trx':v_id_payment,'status':'SUCCESS',
                                    'user':v_phone_number,
                                    'transaction_type':'DEBIT',
                                    'amount':v_amount,
                                    'remarks':v_remarks,
                                    'balance_before':v_balance_before,
                                    'balance_after':v_balance_after,
                                    'created_date':v_created_date})
            return responseJSON(200,'T','Success',{'payment_id':v_id_payment,'amount':v_amount,
                                            'remarks':v_remarks,'balance_before':v_balance_before,
                                            'balance_after':v_balance_after,
                                            'created_date':v_created_date})
    except Exception as error:
        db.history.insert_one({'id_trx':v_id_payment,'status':'FAILED',
                                    'user':v_phone_number,
                                    'transaction_type':'DEBIT',
                                    'amount':v_amount,
                                    'remarks':str(error),
                                    'balance_before':v_balance_before,
                                    'balance_after':v_balance_after,
                                    'created_date':v_created_date})
        return responseJSON(400,'F',str(error),[])

@app.route("/transfer",methods=['POST'])
@jwt_required()
def transfer():
    current_user = get_jwt_identity()
    try:
        v_raw = json.loads(request.get_data())
        v_target_user = v_raw['v_target_user']
        v_amount = v_raw['v_amount']
        v_remarks = v_raw['v_remarks']
        v_phone_number = current_user
        v_id_transfer = get_random_string(10)
        data_saldo = db.saldo.find_one({"phone_number": v_phone_number})
        data_saldo_target = db.saldo.find_one({"phone_number": v_target_user})
        v_balance_before = data_saldo['amount']
        v_balance_after = (data_saldo['amount'] - v_amount)
        v_balance_after_target = (data_saldo_target['amount'] + v_amount)
        if v_balance_after < 0:
            return responseJSON(400,'F','Balance is not enough',[])
        else:
            db.saldo.update_one({'phone_number': v_phone_number}, {"$set": {'amount': v_balance_after}})
            db.saldo.update_one({'phone_number': v_target_user}, {"$set": {'amount': v_balance_after_target}})
           
            v_created_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db.history.insert_one({'id_trx':v_id_transfer,'status':'SUCCESS',
                                    'user':v_phone_number,
                                    'transaction_type':'DEBIT',
                                    'amount':v_amount,
                                    'remarks':v_remarks,
                                    'balance_before':v_balance_before,
                                    'balance_after':v_balance_after,
                                    'created_date':v_created_date})
            return responseJSON(200,'T','Success',{'transfer_id':v_id_transfer,'target':v_target_user,
                                            'amount':v_amount,
                                            'remarks':v_remarks,'balance_before':v_balance_before,
                                            'balance_after':v_balance_after,
                                            'created_date':v_created_date})
    except Exception as error:
        db.history.insert_one({'id_trx':v_id_transfer,'status':'FAILED',
                                'user':v_phone_number,
                                'transaction_type':'DEBIT',
                                'amount':v_amount,
                                'remarks':str(error),
                                'balance_before':v_balance_before,
                                'balance_after':v_balance_after,
                                'created_date':v_created_date})
        return responseJSON(400,'F',str(error),[])

@app.route("/profile",methods=['PUT'])
@jwt_required()
def profile():
    current_user = get_jwt_identity()
    try:
        v_raw = json.loads(request.get_data())
        v_first_name = v_raw['v_first_name']
        v_last_name = v_raw['v_last_name']
        v_address = v_raw['v_address']
        v_phone_number = current_user
        v_user_id = get_random_string(10)
        data_user = db.todos.find_one({"phone_number": v_phone_number})
       
        db.todos.update_one({'phone_number': v_phone_number}, {"$set": {'first_name': v_first_name,
                                                                        'last_name':v_last_name,
                                                                        'address':v_address}})
           
        v_created_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return responseJSON(200,'T','Success',{'user_id':v_user_id,'first_name':v_first_name,
                            'last_name':v_last_name,'address':v_address,
                            'updated_date':v_created_date})
    except Exception as error:
        return responseJSON(400,'F',str(error),[])

@app.route("/transactions",methods=['GET'])
@jwt_required()
def transactions():
    current_user = get_jwt_identity()
    history = db.history.find()
    print(history)
    dt = []
    for todo in history:
        print(todo)
        dictDt={}
        dictDt['id_trx'] = todo['id_trx']
        dictDt['status']=todo['status']
        dictDt['user'] = todo['user']
        dictDt['transaction_type']=todo['transaction_type']
        dictDt['amount']=todo['amount']
        dictDt['remarks'] = todo['remarks']
        dictDt['balance_before']=todo['balance_before']
        dictDt['balance_after'] = todo['balance_after']
        dictDt['created_date']=todo['created_date']
        dt.append(dictDt)
    return jsonify(dt)

# Hanya untuk cek data sementara
@app.route("/",methods=['GET','POST'])
def home():
    todos = db.todos.find()
    print(todos)
    dt = []
    for todo in todos:
        print(todo)
        dictDt={}
        dictDt['v_fist_name'] = todo['first_name']
        dictDt['v_last_name']=todo['last_name']
        dictDt['v_phone_number'] = todo['phone_number']
        dictDt['v_address']=todo['address']
        dictDt['v_pin']=todo['pin']
        dt.append(dictDt)
    return jsonify(dt)

# Hanya untuk cek data sementara
@app.route("/saldo",methods=['GET','POST'])
def saldo():
    saldo = db.saldo.find()
    dt = []
    for todo in saldo:
        dictDt={}
        dictDt['v_phone_number'] = todo['phone_number']
        dictDt['v_amount']=todo['amount']
        dt.append(dictDt)
    return jsonify(dt)


# Hanya untuk hapus data sementara
@app.route("/hapus_data", methods=['DELETE'])
def hapus_data():
    v_raw = json.loads(request.get_data())
    v_phone_number = v_raw['v_phone_number']
    todo = db.saldo.delete_one({'phone_number': v_phone_number})
    return todo.raw_result


if __name__ == "__main__":
    app.run(debug=True)