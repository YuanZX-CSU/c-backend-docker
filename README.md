# 概览

本仓库分为两个部分 c-backend ，c-redis 。

c-backend 是 [c-render-vue](http://vlab.csu.edu.cn/git/YuanZhixiang/c-render-vue) 的 Web 后端。

c-backend 内的核心分析器不支持多线程，作为 Web 后端也没有添加多线程支持。

可以单独运行一个 c-backend 容器用于测试。在实际使用中，建议使用 Docker Swarm 部署集群来支持多线程，同时可搭配 c-redis 实现缓存功能。

# 部署

构建 c-backend 镜像（/c-backend 目录下）：
```
sudo docker build -t c-backend:latest .
```

构建 c-redis 镜像（/c-redis 目录下）：
```
sudo docker build -t c-redis:latest .
```

前置步骤：Docker Swarm 初始化（初次使用时）：
```
sudo docker swarm init
```

（可选）查看已存在的 Docker Network：
```
sudo docker network ls
```

创建 Docker Network 用于连通 c-backend 和 c-redis：
```
sudo docker network create -d overlay c-network
```

（可选）删除之前的服务：
```
sudo docker service rm c-backend-service
sudo docker service rm c-redis-service
```

（可选）检查是否删除完毕，查看正在运行的容器：
```
sudo docker ps
```

创建 c-redis 服务：
```
sudo docker service create --name c-redis-service --network c-network -p 6379:6379 c-redis:latest
```

创建 c-backend 服务：（--limit-memory 单个实例的内粗限制）（--replicas 副本数量，建议设置为 `线程数 - 1`）
```
sudo docker service create --name c-backend-service --network c-network --limit-memory=4GB --replicas 7 -p 5000:5000 c-backend:latest
```

# 检查

部署完成后，可访问 ip:5000/state 查看部署结果。

预期结果：
```
OK.
redis_available: True
```

# 备注

后端为http协议，请自行代理为https

后端设置为完全允许跨域

# 请求

### 获取后端状态

路径：`/state`

方法：`GET`

返回：`string:` `OK.<br>redis_available: [True/False]`

### 分析代码

路径：`/visualize`

方法：`POST`

请求：form-data: 

`code`：`代码`

`stdin`：`测试用例`(可选)

返回：`json:` `{...json...}`

# 额外文件

仓库内含有几个额外文件，其目的是减少构建时的网络影响。

下面列出了文件来源，可自行下载检查。

`c_backend.tar.gz`：

来自仓库 https://github.com/pathrise-eng/pathrise-python-tutor/tree/master/v4-cokapi/backends/c_cpp 的代码打包。

`openssl-3.2.1.tar`：

来自 https://www.openssl.org/source/openssl-3.2.1.tar.gz ，下载后得到的是 `openssl-3.2.1.tar.tar`。

`Python-3.12.2.tgz`：

来自 https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tgz 。

# Redis 配置

仓库中的 `redis.conf` 相对于默认配置，做出了以下修改 :

```
# bind 127.0.0.1 ::1
protected-mode no
requirepass c-backend
maxmemory 1gb
```