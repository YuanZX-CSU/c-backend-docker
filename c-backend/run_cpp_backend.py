# -*- coding: UTF-8 -*-
# 使用Valgrind为基础，运行OPT的C/C++后端，并将JSON输出到stdout以便于管
# 道传输到web应用中，同时妥善处理错误情况。
#
# 创建日期：2016-05-09

import json
import os
from subprocess import Popen, PIPE
import re
import sys
import uuid
import shutil

# 定义用于匹配Valgrind输出的正则表达式
VALGRIND_MSG_RE = re.compile('==\d+== (.*)$')
end_of_trace_error_msg = None

# 获取当前脚本的目录，确保可执行文件路径总是相对的
DN = os.path.dirname(sys.argv[0])
if not DN:
    DN = '.' # 所以我们总是有一个类似 ./usercode.exe 的可执行文件路径
USER_PROGRAM = sys.argv[1] # 要运行的程序字符串
LANG = sys.argv[2] # 'c' 表示C语言，'cpp' 表示C++语言

# 新增随机目录
uuid = str(uuid.uuid4())
RANDOM_DIR = DN + '/' + uuid
os.makedirs(RANDOM_DIR)

# 添加输入用例功能
input_data = None
if len(sys.argv) > 3:
    input_data = sys.argv[3]

# 命令行参数是否启用美化输出
prettydump = False
# 仅美化终端输出内容，不影响实际结果，此参数位置用于输入用例
# if len(sys.argv) > 3:
#     if sys.argv[3] == '--prettydump':
#         prettydump = True

# 根据编程语言选择编译器和语言标准
if LANG == 'c':
    CC = 'gcc'
    DIALECT = '-std=c11'
    FN = 'usercode.c'
else:
    CC = 'g++'
    DIALECT = '-std=c++11'
    FN = 'usercode.cpp'

# 拼接各种文件路径
# 此处使用随机路径
# F_PATH = os.path.join(DN, FN)
# VGTRACE_PATH = os.path.join(DN, 'usercode.vgtrace')
# EXE_PATH = os.path.join(DN, 'usercode.exe')
F_PATH = os.path.join(RANDOM_DIR, FN)
VGTRACE_PATH = os.path.join(RANDOM_DIR, 'usercode.vgtrace')
EXE_PATH = os.path.join(RANDOM_DIR, 'usercode.exe')

# 删除旧文件，避免使用错误的文件
for f in (F_PATH, VGTRACE_PATH, EXE_PATH):
    if os.path.exists(f):
        os.remove(f)

# 将USER_PROGRAM写入到F_PATH中
with open(F_PATH, 'w') as f:
    f.write(USER_PROGRAM)

# 编译用户代码
p = Popen([CC, DIALECT, '-ggdb', '-O0', '-fno-omit-frame-pointer', '-o', EXE_PATH, F_PATH],
          stdout=PIPE, stderr=PIPE)
(gcc_stdout, gcc_stderr) = p.communicate()
gcc_retcode = p.returncode

# 输出gcc的错误信息
if gcc_retcode == 0:
    # 防止输出多余信息
    # print >> sys.stderr, '=== gcc stderr ==='
    # print >> sys.stderr, gcc_stderr
    # print >> sys.stderr, '==='

    if input_data is None:
        input_data = '' 
        
    # 使用Valgrind运行编译后的代码
    VALGRIND_EXE = os.path.join(DN, 'valgrind-3.11.0/inst/bin/valgrind')
    valgrind_p = Popen(['stdbuf', '-o0', # 确保stdout不会被缓冲，以便正确追踪
                        VALGRIND_EXE,
                        '--tool=memcheck',
                        '--source-filename=' + FN,
                        '--trace-filename=' + VGTRACE_PATH,
                        EXE_PATH],
                    stdout=PIPE,
                    stdin=PIPE,
                    stderr=PIPE)
    valgrind_p.stdin.write(input_data)
    (valgrind_stdout, valgrind_stderr) = valgrind_p.communicate()
    valgrind_retcode = valgrind_p.returncode

    # 输出Valgrind的错误信息
    # 防止输出多余信息
    # print >> sys.stderr, '=== Valgrind stdout ==='
    # print >> sys.stderr, valgrind_stdout
    # print >> sys.stderr, '=== Valgrind stderr ==='
    # print >> sys.stderr, valgrind_stderr

    # 处理Valgrind检测到的错误
    error_lines = []
    in_error_msg = False
    if valgrind_retcode != 0: # 如果Valgrind运行出错
        for line in valgrind_stderr.splitlines():
            m = VALGRIND_MSG_RE.match(line)
            if m:
                msg = m.group(1).rstrip()
                # 如果检测到进程终止错误，则记录后续错误信息
                if 'Process terminating' in msg:
                    in_error_msg = True

                if in_error_msg:
                    if not msg:
                        in_error_msg = False

                if in_error_msg:
                    error_lines.append(msg)

        if error_lines:
            end_of_trace_error_msg = '\n'.join(error_lines)

    # 将Valgrind追踪文件转换为OPT追踪格式
    # TODO: 考虑将这部分集成到同一个脚本中，因为它是Python代码，无需作为外部脚本调用
    POSTPROCESS_EXE = os.path.join(DN, 'vg_to_opt_trace.py')
    args = ['python', POSTPROCESS_EXE]
    if prettydump:
        args.append('--prettydump')
    else:
        args.append('--jsondump')
    if end_of_trace_error_msg:
        args += ['--end-of-trace-error-msg', end_of_trace_error_msg]
    args.append(F_PATH)

    postprocess_p = Popen(args, stdout=PIPE, stderr=PIPE)
    (postprocess_stdout, postprocess_stderr) = postprocess_p.communicate()
    postprocess_retcode = postprocess_p.returncode
    # 防止输出多余信息
    # print >> sys.stderr, '=== postprocess stderr ==='
    # print >> sys.stderr, postprocess_stderr
    # print >> sys.stderr, '==='

    print postprocess_stdout
else:
    # 输出gcc错误信息，并优雅地解析并报告编译错误
    # 防止输出多余信息
    # print >> sys.stderr, '=== gcc stderr ==='
    # print >> sys.stderr, gcc_stderr
    # print >> sys.stderr, '==='
    exception_msg = 'unknown compiler error'
    lineno = None
    column = None

    # 只报告能够检测到行和列号的第一行错误
    for line in gcc_stderr.splitlines():
        m = re.search(FN + ':(\d+):(\d+):.+?(error:.*$)', line)
        if m:
            lineno = int(m.group(1))
            column = int(m.group(2))
            exception_msg = m.group(3).strip()
            break

        # 链接错误通常是 'undefined ' 某某
        if 'undefined ' in line:
            parts = line.split(':')
            exception_msg = parts[-1].strip()
            # 匹配类似如下的错误信息
            # /home/pgbovine/opt-cpp-backend/./usercode.c:2: undefined reference to `asdf'
            if FN in parts[0]:
                try:
                    lineno = int(parts[1])
                except:
                    pass
            break

    ret = {'code': USER_PROGRAM,
           'trace': [{'event': 'uncaught_exception',
                    'exception_msg': exception_msg,
                    'line': lineno}],
            'gcc_stderr': gcc_stderr}
    print json.dumps(ret)

# 清理临时随机文件夹
if os.path.exists(RANDOM_DIR) and os.path.isdir(RANDOM_DIR):
    shutil.rmtree(RANDOM_DIR)