# B站桌面弹幕播放器

一个基于 Electron 的桌面B站视频播放器，支持DASH流播放和弹幕显示。

## 功能特性

- 支持通过BV号或视频链接播放B站视频
- 支持DASH流媒体格式播放
- 弹幕从右向左滚动显示
- 弹幕与视频容器区域交互（进入视频区域自动隐藏）
- 系统托盘控制
- 评论查看功能
- 鼠标穿透模式（可与桌面图标交互）

## 技术栈

### 前端
- Electron - 跨平台桌面应用框架
- dash.js - DASH流媒体播放器
- flv.js - FLV格式支持
- hls.js - HLS格式支持
- Socket.IO - 实时通信

### 后端
- Python Flask - Web服务框架
- Flask-SocketIO - WebSocket支持
- Requests - HTTP请求库

## 项目结构

```
bilibili-desk/
├── main.js          # Electron主进程
├── preload.js       # 预加载脚本
├── index.html       # 主页面
├── renderer.js      # 渲染进程逻辑
├── package.json     # Node.js配置
├── backend/         # Python后端
│   ├── app.py       # Flask应用入口
│   ├── bilibili_api.py  # B站API封装
│   ├── constant.py  # 常量配置
│   ├── error_code.py # 错误码定义
│   ├── result.py    # 响应结果封装
│   └── requirements.txt # Python依赖
└── icon/            # 图标资源
```

## 安装与运行

### 环境要求

- Node.js 16+
- Python 3.8+

### 安装依赖

```bash
# 安装前端依赖
npm install

# 安装后端依赖
cd backend
pip install -r requirements.txt
```

### 运行应用

```bash
# 启动后端服务
cd backend
python app.py

# 在另一个终端启动Electron应用
npm start
```

### 打包应用

```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux
```

## 使用说明

1. 启动应用后，在底部输入框输入BV号或B站视频链接
2. 点击"播放"按钮加载视频
3. 弹幕会自动从右向左滚动显示
4. 鼠标悬停在弹幕上会高亮显示
5. 点击系统托盘图标可以暂停弹幕、切换视频源等

## 系统托盘菜单

- 暂停弹幕 - 暂停/恢复弹幕显示
- 切换视频源 - 快速切换输入框焦点
- 显示/隐藏窗口 - 控制窗口显示
- 退出 - 关闭应用

## API说明

后端服务运行在 `http://localhost:5000`

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/video/info/<bvid>` | GET | 获取视频信息 |
| `/api/video/stream/<bvid>/<cid>` | GET | 获取视频流信息 |
| `/api/video/audio/<bvid>/<cid>` | GET | 获取音频流信息 |
| `/api/danmaku/<bvid>/<cid>` | GET | 获取弹幕数据 |
| `/api/comments/<oid>` | GET | 获取评论 |
| `/api/mpd/<bvid>` | GET | 获取MPD清单 |
| `/api/stream/video/<bvid>` | GET | 视频流代理 |
| `/api/stream/audio/<bvid>` | GET | 音频流代理 |

### WebSocket事件

| 事件 | 方向 | 说明 |
|------|------|------|
| `play_video` | 客户端→服务端 | 请求播放视频 |
| `video_info` | 服务端→客户端 | 视频信息 |
| `video_stream` | 服务端→客户端 | 视频流信息 |
| `audio_stream` | 服务端→客户端 | 音频流信息 |
| `danmaku_data` | 服务端→客户端 | 弹幕数据 |
| `status` | 服务端→客户端 | 状态消息 |
| `error` | 服务端→客户端 | 错误消息 |

## 注意事项

- 本项目仅供学习交流使用
- 请遵守B站用户协议和相关法律法规
- 视频内容版权归原作者所有

## License

MIT
