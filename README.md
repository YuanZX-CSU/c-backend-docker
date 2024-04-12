## 构建单个基础镜像

核心分析器不支持多线程，Web后端也没有添加多线程支持

构建镜像
```
sudo docker build -t c-backend:latest .
```

运行镜像
```
sudo docker run -d -p 5000:5000 c-backend:latest
```

临时前台运行镜像
```
sudo docker run -it -p 5000:5000 c-backend:latest
```

## 运行集群

初始化
```
sudo docker swarm init
```

创建服务 (--replicas 实例数量)
```
sudo docker service create --name c-backend-service --replicas 8 -p 5000:5000 c-backend:latest
```

删除服务
```
sudo docker service rm c-backend-service
```

## 额外

后端为http，请自行代理为https

后端设置为完全允许跨域

## 请求

#### 获取后端状态

路径: `/state`

方法: `GET`

返回: `OK`

#### 分析代码

路径: `/visualize`

方法: `POST`

请求: form-data: 

`code` : `代码`

`stdin` : `测试用例`(可选)

返回: `{...json...}`

## 文件列表

`c_backend.tar.gz`

来自仓库 [https://github.com/pathrise-eng/pathrise-python-tutor ](https://github.com/pathrise-eng/pathrise-python-tutor/tree/master/v4-cokapi/backends/c_cpp) 的部分代码打包，减少构建时的网络影响

`openssl-3.2.1.tar`

来自相关网站，减少构建时的网络影响

`Python-3.12.2.tgz`

来自相关网站，减少构建时的网络影响

`backend.py`

后端脚本

`run_cpp_backend.py`

替换`c_backend.tar.gz`里原有的脚本，使其适配后端