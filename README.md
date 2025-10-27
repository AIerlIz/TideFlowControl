# TideFlowControl

TideFlowControl 是一个同时支持 HTTP 和 Torrent 协议的下载器，流式下载，不写入磁盘。

## 功能特性

- 通过 HTTP/HTTPS 下载文件
- 通过 Torrent 文件或磁力链接下载文件
- 流式下载，不写入磁盘
- 配置简单
- 支持 Docker 快速部署

## 安装

1.  克隆仓库：
    ```bash
    git clone https://github.com/AIerlIz/TideFlowControl.git
    cd TideFlowControl
    ```

2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

## 使用方法

运行主脚本：

```bash
python main.py
```

## 配置

您可以通过编辑 `config.py` 文件或在 `.env` 文件中设置环境变量来配置此应用。

## Docker 支持

您也可以使用 Docker 来运行此应用。

1.  构建 Docker 镜像：
    ```bash
    docker build -t tideflowcontrol .
    ```

2.  运行 Docker 容器：
    ```bash
    docker run -d --name tideflowcontrol tideflowcontrol
    ```

或者，您可以使用 Docker Compose：

```bash
docker-compose up -d
