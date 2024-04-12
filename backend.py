from flask import Flask, request
import subprocess
import json
from gevent.pywsgi import WSGIServer
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# 用于测试后端是否正常运行
@app.route('/state')
def hello_world():
    return 'OK'


@app.route('/visualize', methods=['POST'])
def visualize():
    # 获取POST内容
    code = request.form.get('code', None)  # 测试的代码
    stdin = request.form.get('stdin', '')  # 用例输入（如果有）

    # 校验测试的代码
    if code is None:
        return {'error': 'Code does not exist.'}

    # 执行分析脚本
    result = run_python2_script_and_get_output(code, stdin)
    if result is None:
        return {'error': 'Analysis failed.'}
    else:
        if len(result) == 0:
            return {'error': 'Analysis failed.'}
        else:
            return json.loads(result)


# 调用核心分析脚本
def run_python2_script_and_get_output(code, stdin):
    script_path = './run_cpp_backend.py'
    python2_interpreter = '/usr/bin/python2'

    process = subprocess.Popen([python2_interpreter, script_path, code, 'c', stdin], stdout=subprocess.PIPE)

    output, error = process.communicate()
    if process.returncode != 0:
        # raise Exception('Python 2 script failed with error: {}'.format(error.decode('utf-8')))
        return None

    return output.decode('utf-8')


if __name__ == '__main__':
    print('c-backend server start.')
    # 启动后端
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
