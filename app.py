# app.py
import json
import cv2
import os
import threading
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# 全局变量
app = Flask(__name__)
app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 新增全局变量，用于计算
flame_signal = 0
flame_stability = 0
flame_length = 0
flame_width = 0
flame_area = 0
average_temp = 0

recording = False
output_path = 'output_pseudocolor.avi'
video_writer = None
lock = threading.Lock()  # 用于同步多线程录制操作

# 新增全局变量，用于切换摄像头
camera_index = 0
cap = cv2.VideoCapture(camera_index)

# 数据库，用于存储用户信息
USER_FILE = 'users.json'
if not os.path.exists(USER_FILE):
    with open(USER_FILE, 'w') as file:
        json.dump({}, file)

with open(USER_FILE, 'r') as file:
    users = json.load(file)
    print(users)

class User(UserMixin):
    def __init__(self, id):
        self.id = id
# 用于用户加载
@login_manager.user_loader
def load_user(username):
    return User(username) if username in users else None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash('Username already exists')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            users[username] = {'password': hashed_password}
            with open(USER_FILE, 'w') as file:
                json.dump(users, file)

            flash('Registration successful! Please login.')
            return redirect(url_for('login'))

    return render_template('register.html')

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users.get(username) # get方法用于返回指定键的值，如果值不在字典中返回默认值None
        if user and bcrypt.check_password_hash(user['password'], password):
            user_obj = User(username)
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 主页,@login_required若不登录就会跳转到登录页面
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('index.html')

@app.route('/video_feed_original')
def video_feed_original():
    # 原始视频流响应
    return Response(generate_original_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_pseudocolor')
def video_feed_pseudocolor():


    # 伪彩色视频流响应
    return Response(generate_pseudocolor_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# 生成原始帧
def generate_original_frames():

    if not cap.isOpened():
        print("无法打开摄像头")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break

        # 将帧编码为JPEG格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # 使用multipart格式返回视频流
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

# 生成处理后的帧
def generate_pseudocolor_frames():
    global video_writer

    #异常处理
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break

        # 将原始帧转换为灰度图像
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 应用伪彩色映射
        pseudocolor_frame = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

        # 录制伪彩色视频帧
        if recording:
            with lock:
                if video_writer is not None:
                    video_writer.write(pseudocolor_frame)

        # 计算火焰特性
        calculate_flame_properties(pseudocolor_frame)

        # 将帧编码为JPEG格式
        ret, buffer = cv2.imencode('.jpg', pseudocolor_frame)
        pseudocolor_frame = buffer.tobytes()

        # 使用multipart格式返回视频流
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + pseudocolor_frame + b'\r\n')

    cap.release()

# 从帧中计算火焰特性
def calculate_flame_properties(frame):
    global flame_signal, flame_stability, flame_length, flame_width, flame_area, average_temp

    # 将帧转换为灰度图像
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 简单的二值化处理，用于分割火焰
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # 计算火焰轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # 找到最大的轮廓（假设是火焰区域）
        largest_contour = max(contours, key=cv2.contourArea)

        # 计算火焰的边界框
        x, y, w, h = cv2.boundingRect(largest_contour)
        flame_length = h
        flame_width = w
        flame_area = cv2.contourArea(largest_contour)

        # 假设火焰的亮度代表温度，计算平均亮度
        average_temp = np.mean(gray[y:y+h, x:x+w])

        # 假设火焰面积的变化反映了燃烧信号和稳定性
        flame_signal = min(100, flame_area / (gray.shape[0] * gray.shape[1]) * 100)
        flame_stability = min(100, 100 - np.std(gray[y:y+h, x:x+w]) / 255 * 100)

        # 保留两位小数（只对有小数部分的值）
        flame_signal = round(flame_signal, 2)
        flame_stability = round(flame_stability, 2)
        flame_length = round(flame_length, 2) if isinstance(flame_length, float) else flame_length
        flame_width = round(flame_width, 2) if isinstance(flame_width, float) else flame_width
        flame_area = round(flame_area, 2) if isinstance(flame_area, float) else flame_area
        average_temp = round(average_temp, 2)
    return flame_signal, flame_stability, flame_length, flame_width, flame_area, average_temp

# 新增API用于返回火焰参数
@app.route('/get_flame_properties', methods=['GET'])
def get_flame_properties():
    return {
        'flame_signal': flame_signal,
        'flame_stability': flame_stability,
        'flame_length': flame_length,
        'flame_width': flame_width,
        'flame_area': flame_area,
        'average_temp': average_temp
    }

# 录制视频
@app.route('/toggle_recording', methods=['POST'])
def toggle_recording():
    global recording, video_writer

    data = request.get_json()
    recording = data['recording']

    if recording:
        # 开始录制
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))
        message = 'Recording started'
    else:
        # 停止录制
        with lock:
            if video_writer is not None:
                video_writer.release()
                video_writer = None
        message = 'Recording stopped'

    return {'message': message}

@app.route('/switch_camera', methods=['POST'])
def switch_camera():
    global camera_index, cap

    # 切换摄像头索引
    camera_index = 1 if camera_index == 0 else 0
    cap.release()  # 释放当前摄像头

    # 重新打开新的摄像头
    cap = cv2.VideoCapture(camera_index)

    return {'camera_index': camera_index}

# 运行
if __name__ == '__main__':
    app.run(debug=True)
'''
export requirement
pip freeze > requirements.txt
pack it as .exe
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" app.py
'''