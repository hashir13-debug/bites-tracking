from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__)
CORS(app)

# Vercel par SQLite database ko /tmp folder mein rakhna parta hai 
# taake temporary files ban saken, warna error aayega.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join('/tmp', 'rider_system_final.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20)) 
    last_device = db.Column(db.String(255), default="No Login Yet")

class Rider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    code = db.Column(db.String(10), unique=True)
    status = db.Column(db.String(50), default="Available")
    device_info = db.Column(db.String(255), default="Not Registered")
    r_time = db.Column(db.String(50), default="--")
    a_time = db.Column(db.String(50), default="--")
    last_click_dt = db.Column(db.DateTime, default=datetime.utcnow() - timedelta(minutes=10))

# Database initialization function
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role='superadmin').first():
            db.session.add(User(email="super@test.com", password="123", role="superadmin"))
            db.session.commit()

init_db()

@app.route('/')
def home():
    return "Bites4Life API is Running!"

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    u = User.query.filter_by(email=data['email'], password=data['password']).first()
    if u:
        u.last_device = request.headers.get('User-Agent', 'Web Browser')
        db.session.commit()
        return jsonify({"role": u.role, "email": u.email})
    return jsonify({"error": "Invalid Credentials"}), 401

@app.route('/check_code/<code>', methods=['GET'])
def check_code(code):
    r = Rider.query.filter_by(code=code).first()
    if r: return jsonify({"success": True, "name": r.name})
    return jsonify({"success": False}), 404

@app.route('/get_admins', methods=['GET'])
def get_admins():
    admins = User.query.filter_by(role='admin').all()
    return jsonify([{"id": a.id, "email": a.email, "device": a.last_device} for a in admins])

@app.route('/add_admin', methods=['POST'])
def add_admin():
    data = request.json
    db.session.add(User(email=data['email'], password=data['password'], role='admin'))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/delete_admin/<int:id>', methods=['DELETE'])
def delete_admin(id):
    u = User.query.get(id)
    if u:
        db.session.delete(u)
        db.session.commit()
    return jsonify({"success": True})

@app.route('/get_riders', methods=['GET'])
def get_riders():
    riders = Rider.query.all()
    return jsonify([{"name": r.name, "code": r.code, "status": r.status, "r_time": r.r_time, "a_time": r.a_time, "device": r.device_info} for r in riders])

@app.route('/add_rider', methods=['POST'])
def add_rider():
    code = str(random.randint(1000, 9999))
    db.session.add(Rider(name=request.json['name'], code=code))
    db.session.commit()
    return jsonify({"code": code})

@app.route('/admin/on_route', methods=['POST'])
def set_on_route():
    r = Rider.query.filter_by(code=request.json['code']).first()
    if r:
        r.status = "On Route"
        r.a_time = datetime.now().strftime("%I:%M %p")
        db.session.commit()
    return jsonify({"success": True})

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    r = Rider.query.filter_by(code=data['code']).first()
    if not r: return jsonify({"error": "Invalid Code"}), 404
    if datetime.utcnow() < r.last_click_dt + timedelta(minutes=5):
        return jsonify({"error": "Wait 5 mins"}), 403
    if r.device_info == "Not Registered":
        r.device_info = request.headers.get('User-Agent', 'Mobile/App')
    r.status = data['status']
    r.r_time = datetime.now().strftime("%I:%M %p")
    r.last_click_dt = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})

@app.route('/delete_rider/<code>', methods=['DELETE'])
def delete_rider(code):
    r = Rider.query.filter_by(code=code).first()
    if r:
        db.session.delete(r)
        db.session.commit()
    return jsonify({"success": True})

# Vercel ko ye line lazmi chahiye
app = app