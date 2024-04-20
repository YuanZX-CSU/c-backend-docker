# 基础镜像，必须选择ubuntu14，在高版本ubuntu中c_backend不能编译成功
FROM ubuntu:14.04.1

RUN apt-get update && apt-get install -y \
  build-essential \
  autotools-dev \
  automake \
  libc6-dbg \
  python \
  zlib1g-dev

RUN mkdir /app
WORKDIR /app

COPY ./c_backend.tar.gz ./
COPY ./openssl-3.2.1.tar ./
COPY ./Python-3.12.2.tgz ./

# 合并为一个RUN命令，减少镜像大小
RUN tar -zxf c_backend.tar.gz && \
  tar -xf openssl-3.2.1.tar && \
  tar -zxf Python-3.12.2.tgz && \
  # 构建c_backend核心分析器
  cd /app/c_backend && ./auto-everything.sh && \
  # 构建openssl，作为python依赖
  cd /app/openssl-3.2.1 && ./config && make -j && make install && \
  echo "/usr/local/lib64/" >> /etc/ld.so.conf && ldconfig && \
  # 构建python3.12
  cd /app/Python-3.12.2 && ./configure && make -j && make install && \
  # 清理多余文件
  cd /app/ && \
  rm -r Python-3.12.2 && \
  rm -r openssl-3.2.1 && \
  rm c_backend.tar.gz && \
  rm openssl-3.2.1.tar && \
  rm Python-3.12.2.tgz

# 安装依赖
RUN pip3.12 install flask
RUN pip3.12 install flask-cors
RUN pip3.12 install gevent
RUN pip3.12 install psutil
RUN pip3.12 install redis

# 替代旧的分析脚本（python2）
COPY ./run_cpp_backend.py ./c_backend/

# 加入新的网页后端脚本（python3）
COPY ./backend.py ./c_backend/

# 设定自启动
WORKDIR /app/c_backend
ENTRYPOINT ["python3.12", "./backend.py"]