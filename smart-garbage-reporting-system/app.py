from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import os
import uuid
import random

from datetime import datetime
from random import randint

# =========================
# APP
# =========================

app = Flask(__name__)

app.secret_key = "super_secret_key_123"

# =========================
# DATABASE
# =========================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(BASE_DIR, 'smart_garbage.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

DB = SQLAlchemy(app)

# =========================
# OTP STORAGE
# =========================

otp_storage = {}

# =========================
# UPLOADS
# =========================

UPLOAD_FOLDER = os.path.join('static', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# USER TABLE
# =========================

class User(DB.Model):

    id = DB.Column(DB.Integer, primary_key=True)

    name = DB.Column(DB.String(100), nullable=False)

    mobile = DB.Column(DB.String(20), unique=True, nullable=False)

    password = DB.Column(DB.String(255))

    role = DB.Column(DB.String(20), nullable=False)

    live_latitude = DB.Column(DB.String(50))

    live_longitude = DB.Column(DB.String(50))

    is_active = DB.Column(DB.Boolean, default=False)

# =========================
# REPORT TABLE
# =========================

class Report(DB.Model):

    id = DB.Column(DB.String(100), primary_key=True)

    description = DB.Column(DB.Text, nullable=False)

    location = DB.Column(DB.String(255))

    latitude = DB.Column(DB.String(50))

    longitude = DB.Column(DB.String(50))

    image = DB.Column(DB.String(255))

    status = DB.Column(DB.String(50), default='Pending')

    ai_detected = DB.Column(DB.String(100))

    timestamp = DB.Column(DB.String(100))

# =========================
# CREATE DATABASE
# =========================

with app.app_context():

    DB.create_all()

    admin_exists = User.query.filter_by(
        mobile='9133820788'
    ).first()

    if not admin_exists:

        admin = User(

            name='Upparapati Vishnu',

            mobile='9133820788',

            password=generate_password_hash('admin123'),

            role='admin'

        )

        DB.session.add(admin)
        DB.session.commit()

# =========================
# HOME
# =========================

@app.route('/')
def home():

    return render_template('index.html')

# =========================
# ADMIN PAGE
# =========================

@app.route('/admin')
def admin():

    if session.get('role') != 'admin':

        return redirect('/admin-login')

    return render_template('admin.html')

# =========================
# WORKER PAGE
# =========================

@app.route('/worker')
def worker():

    if session.get('role') != 'worker':

        return redirect('/worker-login')

    return render_template('worker.html')

# =========================
# LOGIN PAGES
# =========================

@app.route('/admin-login')
def admin_login():

    return render_template('admin_login.html')

@app.route('/worker-login')
def worker_login():

    return render_template('worker_login.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():

    mobile = session.get('worker_mobile')

    if mobile:

        worker = User.query.filter_by(
            mobile=mobile
        ).first()

        if worker:

            worker.is_active = False
            DB.session.commit()

    session.clear()

    return redirect('/')

# =========================
# ADMIN LOGIN
# =========================

@app.route('/api/login', methods=['POST'])
def login():

    try:

        data = request.get_json(force=True)

        mobile = data.get('mobile')
        password = data.get('password')

        user = User.query.filter_by(
            mobile=mobile
        ).first()

        if user and user.password:

            if check_password_hash(user.password, password):

                session['role'] = user.role
                session['user_name'] = user.name

                return jsonify({

                    'success': True,
                    'redirect': '/admin'

                })

        return jsonify({

            'success': False,
            'message': 'Invalid Credentials'

        })

    except Exception as e:

        print("ADMIN LOGIN ERROR :", str(e))

        return jsonify({

            'success': False,
            'message': str(e)

        })

# =========================
# SEND WORKER OTP
# =========================

@app.route('/api/send-worker-otp', methods=['POST'])
def send_worker_otp():

    print("SEND OTP API CALLED")

    try:

        data = request.get_json(force=True)

        print("REQUEST DATA :", data)

        mobile = data.get('mobile')

        if not mobile:

            print("MOBILE NOT FOUND")

            return jsonify({
                'success': False,
                'message': 'Mobile Required'
            })

        otp = str(randint(1000,9999))

        otp_storage[mobile] = otp

        print("\n==========================")
        print(" SMART GARBAGE WORKER OTP ")
        print("==========================")
        print("Mobile :", mobile)
        print("OTP    :", otp)
        print("==========================\n")

        return jsonify({

            'success': True,
            'message': 'OTP Sent Successfully'

        })

    except Exception as e:

        print("SEND OTP ERROR :", str(e))

        return jsonify({

            'success': False,
            'message': str(e)

        })

# =========================
# VERIFY WORKER OTP
# =========================

@app.route('/api/verify-worker-otp', methods=['POST'])
def verify_worker_otp():

    try:

        data = request.get_json(force=True)

        mobile = data.get('mobile')
        otp = data.get('otp')
        name = data.get('name')

        saved_otp = otp_storage.get(mobile)

        if saved_otp != otp:

            return jsonify({

                'success': False,
                'message': 'Invalid OTP'

            })

        worker = User.query.filter_by(
            mobile=mobile
        ).first()

        if not worker:

            worker = User(

                name=name,
                mobile=mobile,
                role='worker',
                is_active=True

            )

            DB.session.add(worker)

        else:

            worker.name = name
            worker.is_active = True

        DB.session.commit()

        session['role'] = 'worker'
        session['worker_mobile'] = mobile
        session['worker_name'] = name

        otp_storage.pop(mobile, None)

        return jsonify({

            'success': True,
            'redirect': '/worker'

        })

    except Exception as e:

        print("VERIFY OTP ERROR :", str(e))

        return jsonify({

            'success': False,
            'message': str(e)

        })

# =========================
# UPDATE LIVE LOCATION
# =========================

@app.route('/api/update-worker-location', methods=['POST'])
def update_worker_location():

    try:

        if session.get('role') != 'worker':

            return jsonify({
                'success': False
            })

        data = request.get_json(force=True)

        lat = data.get('latitude')
        lng = data.get('longitude')

        mobile = session.get('worker_mobile')

        worker = User.query.filter_by(
            mobile=mobile
        ).first()

        if worker:

            worker.live_latitude = str(lat)
            worker.live_longitude = str(lng)

            DB.session.commit()

            return jsonify({
                'success': True
            })

        return jsonify({
            'success': False
        })

    except Exception as e:

        print("LOCATION ERROR :", str(e))

        return jsonify({
            'success': False
        })

# =========================
# ACTIVE WORKERS
# =========================

@app.route('/api/active-workers')
def active_workers():

    workers = User.query.filter_by(
        role='worker',
        is_active=True
    ).all()

    data = []

    for worker in workers:

        data.append({

            'name': worker.name,
            'mobile': worker.mobile,
            'latitude': worker.live_latitude,
            'longitude': worker.live_longitude

        })

    return jsonify(data)

# =========================
# SUBMIT REPORT
# =========================

@app.route('/api/report', methods=['POST'])
def report():

    try:

        description = request.form.get('description')

        location = request.form.get('location')

        latitude = request.form.get('latitude')

        longitude = request.form.get('longitude')

        image = request.files.get('image')

        report_id = str(uuid.uuid4())

        filename = ""

        if image and image.filename != "":

            safe_name = secure_filename(image.filename)

            filename = report_id + "_" + safe_name

            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )

            image.save(filepath)

        ai_tags = [

            "Plastic Waste",
            "Food Waste",
            "Overflow Bin",
            "Dry Waste"

        ]

        ai_result = random.choice(ai_tags)

        new_report = Report(

            id=report_id,

            description=description,

            location=location,

            latitude=latitude,

            longitude=longitude,

            image=filename,

            status='Pending',

            ai_detected=ai_result,

            timestamp=datetime.now().strftime(
                '%d %b %Y, %I:%M %p'
            )

        )

        DB.session.add(new_report)

        DB.session.commit()

        return jsonify({

            'success': True

        })

    except Exception as e:

        print("REPORT ERROR :", str(e))

        return jsonify({

            'success': False

        })

# =========================
# GET REPORTS
# =========================

@app.route('/api/reports')
def get_reports():

    reports = Report.query.all()

    data = []

    for report in reports:

        data.append({

            'id': report.id,

            'description': report.description,

            'location': report.location,

            'latitude': report.latitude,

            'longitude': report.longitude,

            'image': report.image,

            'status': report.status,

            'ai_detected': report.ai_detected,

            'timestamp': report.timestamp

        })

    return jsonify(data)

# =========================
# UPDATE STATUS
# =========================

@app.route('/api/update-status/<report_id>', methods=['PUT'])
def update_status(report_id):

    try:

        data = request.get_json(force=True)

        report = Report.query.filter_by(
            id=report_id
        ).first()

        if report:

            report.status = data.get('status')

            DB.session.commit()

            return jsonify({
                'success': True
            })

        return jsonify({
            'success': False
        })

    except Exception as e:

        print("STATUS ERROR :", str(e))

        return jsonify({
            'success': False
        })

# =========================
# RUN APP
# =========================

if __name__ == '__main__':

    app.run(debug=True)