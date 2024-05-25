import redis
from flask import Flask, request
import subprocess
import json
from gevent.pywsgi import WSGIServer
from flask_cors import CORS
import psutil
import signal
import os
import shutil

app = Flask(__name__)
CORS(app)

redis_available = False


# 用于测试后端是否正常运行
@app.route('/state')
def hello_world():
    return 'OK.<br>redis_available: ' + str(redis_available)


@app.route('/visualize', methods=['POST'])
def visualize():
    # 获取POST内容
    code = request.form.get('code', None)  # 测试的代码
    stdin = request.form.get('stdin', '')  # 用例输入（如果有）

    # 校验测试的代码
    if code is None:
        return {'error': '你的代码呢？'}

    key = code + '#' + stdin
    if redis_available:
        value = r.get(key)
        if value is not None:
            return json.loads(str(value))

    # 执行分析脚本
    result = run_python2_script_and_get_output(code, stdin)
    if result is None:
        return {'error': '分析失败。'}
    elif len(result) == 0:
        return {'error': '分析失败。'}
    elif result == 'timeout':
        error_message = {'error': '该程序占用过大，请优化后再试。'}
        if redis_available:
            r.set(key, json.dumps(error_message))
            r.expire(key, 3600)
        return error_message
    else:
        if redis_available:
            r.set(key, result)
        return json.loads(result)


# 调用核心分析脚本
def run_python2_script_and_get_output(code, stdin):
    script_path = './run_cpp_backend.py'
    python2_interpreter = '/usr/bin/python2'

    process = subprocess.Popen([python2_interpreter, script_path, code, 'c', stdin], stdout=subprocess.PIPE)

    try:
        output, error = process.communicate(None, 30)
        if process.returncode != 0:
            # raise Exception('Python 2 script failed with error: {}'.format(error.decode('utf-8')))
            return None
        return output.decode('utf-8')
    except subprocess.TimeoutExpired:
        parent_pid = process.pid
        children = psutil.Process(parent_pid).children(recursive=True)
        for child in children:
            child.send_signal(signal.SIGKILL)
        process.send_signal(signal.SIGKILL)
        remove_random_temp_folders()
        return 'timeout'


# 移除 run_cpp_backend.py 创建的随机临时文件夹
def remove_random_temp_folders():
    for item in os.listdir('.'):
        if os.path.isdir(item) and len(item) == 36:
            try:
                shutil.rmtree(item)
            except Exception as remove_random_temp_folders_e:
                print(remove_random_temp_folders_e)


if __name__ == '__main__':
    print('c-backend server start.')
    r = redis.Redis(host='c-redis-service', password='c-backend', port=6379, decode_responses=True)
    try:
        r.ping()
        redis_available = True
        print('redis: connected.')
    except redis.exceptions.ConnectionError as redis_e:
        print('redis: failed.', redis_e)
    # 启动后端
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
