#!/usr/bin/env python3
import requests
import time

# 启动服务器
import subprocess
import os

os.chdir("/Users/xiaohan/Desktop/untitled folder/mini-scheduler")
server = subprocess.Popen([
    "python3", "-m", "uvicorn", "api.main:app", 
    "--host", "127.0.0.1", "--port", "8000"
])

# 等待服务器启动
time.sleep(3)

try:
    # 测试注册
    print("Testing registration...")
    response = requests.post('http://127.0.0.1:8000/auth/register', data={
        'username': 'testuser',
        'password': 'testpass123',
        'confirm': 'testpass123'
    }, allow_redirects=False)
    
    print(f"Registration status: {response.status_code}")
    print(f"Registration response: {response.text}")
    
    if response.status_code == 303:
        print("Registration successful!")
        
        # 检查数据库
        import sqlite3
        conn = sqlite3.connect('data/scheduler.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = 'testuser'")
        user = cursor.fetchone()
        conn.close()
        
        if user:
            print(f"User found in database: {user}")
        else:
            print("User not found in database!")
    
    # 测试登录
    print("\nTesting login...")
    response = requests.post('http://127.0.0.1:8000/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, allow_redirects=False)
    
    print(f"Login status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Login successful! Token: {data.get('access_token', '')[:20]}...")
    
finally:
    server.terminate()
    server.wait()