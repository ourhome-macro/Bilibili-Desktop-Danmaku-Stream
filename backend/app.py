import time
import requests
import threading
from flask import Flask, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from typing import Optional, List

from bilibili_api import BilibiliAPI, VideoInfo, AudioStreamInfo, VideoStreamInfo, DanmakuInfo
from constant import HttpHeader, Server, Stream
from error_code import APIError, ErrorMessage
from result import Result

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bilibili_api = BilibiliAPI()

current_video_info: Optional[VideoInfo] = None
current_audio_info: Optional[AudioStreamInfo] = None
current_video_stream_info: Optional[VideoStreamInfo] = None
current_danmaku_list: List[DanmakuInfo] = []

stream_stats = {
    "total_bytes": 0,
    "start_time": None,
    "current_session_bytes": 0,
}
stream_stats_lock = threading.Lock()


@app.route("/api/video/info/<bvid>", methods=["GET"])
def get_video_info(bvid: str):
    try:
        video_info = bilibili_api.get_video_info(bvid)
        return Result.ok({
            "bvid": video_info.bvid,
            "cid": video_info.cid,
            "title": video_info.title,
            "duration": video_info.duration,
            "owner": video_info.owner,
            "cover": video_info.cover,
            "view_count": video_info.view_count,
            "danmaku_count": video_info.danmaku_count,
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/video/audio/<bvid>/<int:cid>", methods=["GET"])
def get_audio_stream(bvid: str, cid: int):
    try:
        audio_info = bilibili_api.get_audio_stream(bvid, cid)
        return Result.ok({
            "url": audio_info.url,
            "duration": audio_info.duration,
            "bitrate": audio_info.bitrate,
            "sample_rate": audio_info.sample_rate,
            "channels": audio_info.channels,
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/video/stream/<bvid>/<int:cid>", methods=["GET"])
def get_video_stream(bvid: str, cid: int):
    try:
        video_info = bilibili_api.get_video_stream(bvid, cid)
        return Result.ok({
            "url": video_info.url,
            "duration": video_info.duration,
            "width": video_info.width,
            "height": video_info.height,
            "bitrate": video_info.bitrate,
            "mime_type": video_info.mime_type,
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/danmaku/<bvid>/<int:cid>", methods=["GET"])
def get_danmaku(bvid: str, cid: int):
    try:
        danmaku_list = bilibili_api.get_danmaku(bvid, cid)
        return Result.ok({
            "count": len(danmaku_list),
            "danmaku": [
                {
                    "time": d.time,
                    "type": d.type,
                    "color": d.color,
                    "content": d.content,
                    "font_size": d.font_size,
                }
                for d in danmaku_list
            ],
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/comments/<int:oid>", methods=["GET"])
def get_comments(oid: int):
    try:
        page = request.args.get("page", 1, type=int)
        sort = request.args.get("sort", 2, type=int)
        bvid = request.args.get("bvid", "")
        
        data = bilibili_api.get_comments(bvid, oid, page, sort)
        return Result.ok(data).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/player/status", methods=["GET"])
def get_player_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
    }

    if current_video_info:
        status["video_info"] = {
            "bvid": current_video_info.bvid,
            "title": current_video_info.title,
            "duration": current_video_info.duration,
        }

    return Result.ok(status).json()


@app.route("/api/player/stop", methods=["POST"])
def stop_player():
    global current_video_info, current_audio_info, current_video_stream_info, current_danmaku_list

    current_video_info = None
    current_audio_info = None
    current_video_stream_info = None
    current_danmaku_list = []

    return Result.ok().json()


@app.route("/api/stream/audio/<bvid>", methods=["GET"])
def stream_audio(bvid: str):
    global current_audio_info, stream_stats

    if not current_audio_info:
        return Result.bad_request(ErrorMessage.NO_AUDIO_LOADED)

    audio_url = current_audio_info.url
    headers = HttpHeader.stream_headers(bvid)

    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        resp = requests.get(
            audio_url,
            headers=headers,
            stream=True,
            timeout=Stream.TIMEOUT,
        )
        
        print(f"[stream_audio] Request Range: {range_header}")
        print(f"[stream_audio] Response status: {resp.status_code}")

        if resp.status_code == 416:
            print(f"[stream_audio] Error 416: Client requested invalid range {range_header}")
            return Response(
                "Range Not Satisfiable",
                status=416,
                headers={"Content-Type": "text/plain", "Access-Control-Allow-Origin": "*"}
            )

        def generate():
            for chunk in resp.iter_content(chunk_size=Stream.CHUNK_SIZE):
                if chunk:
                    yield chunk
                    with stream_stats_lock:
                        stream_stats["total_bytes"] += len(chunk)
                        stream_stats["current_session_bytes"] += len(chunk)

        response_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Range",
            "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        }
        if "Content-Type" in resp.headers:
            response_headers["Content-Type"] = resp.headers["Content-Type"]
        else:
            response_headers["Content-Type"] = "audio/mp4"
        if "Content-Length" in resp.headers:
            response_headers["Content-Length"] = resp.headers["Content-Length"]
        if "Content-Range" in resp.headers:
            response_headers["Content-Range"] = resp.headers["Content-Range"]
        if "Accept-Ranges" in resp.headers:
            response_headers["Accept-Ranges"] = resp.headers["Accept-Ranges"]
        else:
            response_headers["Accept-Ranges"] = HttpHeader.ACCEPT_RANGES

        return Response(
            generate(),
            status=resp.status_code,
            headers=response_headers,
        )

    except Exception as e:
        print(f"[stream_audio] Error: {e}")
        return Result.server_error(str(e))


@app.route("/api/stream/video/<bvid>", methods=["GET"])
def stream_video(bvid: str):
    global current_video_stream_info, stream_stats

    if not current_video_stream_info:
        return Result.bad_request(ErrorMessage.NO_VIDEO_STREAM)

    video_url = current_video_stream_info.url
    headers = HttpHeader.stream_headers(bvid)

    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        resp = requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=Stream.TIMEOUT,
        )
        
        print(f"[stream_video] Request Range: {range_header}")
        print(f"[stream_video] Response status: {resp.status_code}")

        def generate():
            for chunk in resp.iter_content(chunk_size=Stream.CHUNK_SIZE):
                if chunk:
                    yield chunk
                    with stream_stats_lock:
                        stream_stats["total_bytes"] += len(chunk)
                        stream_stats["current_session_bytes"] += len(chunk)

        response_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Range",
            "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        }
        if "Content-Type" in resp.headers:
            response_headers["Content-Type"] = resp.headers["Content-Type"]
        else:
            response_headers["Content-Type"] = "video/mp4"
        if "Content-Length" in resp.headers:
            response_headers["Content-Length"] = resp.headers["Content-Length"]
        if "Content-Range" in resp.headers:
            response_headers["Content-Range"] = resp.headers["Content-Range"]
        if "Accept-Ranges" in resp.headers:
            response_headers["Accept-Ranges"] = resp.headers["Accept-Ranges"]
        else:
            response_headers["Accept-Ranges"] = HttpHeader.ACCEPT_RANGES

        return Response(
            generate(),
            status=resp.status_code,
            headers=response_headers,
        )

    except Exception as e:
        print(f"[stream_video] Error: {e}")
        return Result.server_error(str(e))


@app.route("/api/stream/stats", methods=["GET"])
def get_stream_stats():
    global stream_stats
    with stream_stats_lock:
        stats = stream_stats.copy()

    elapsed = 0
    if stats["start_time"]:
        elapsed = time.time() - stats["start_time"]

    speed = 0
    if elapsed > 0:
        speed = stats["current_session_bytes"] / elapsed

    return Result.ok({
        "total_bytes": stats["total_bytes"],
        "session_bytes": stats["current_session_bytes"],
        "elapsed_seconds": elapsed,
        "bytes_per_second": speed,
        "total_mb": round(stats["total_bytes"] / 1024 / 1024, 2),
        "session_mb": round(stats["current_session_bytes"] / 1024 / 1024, 2),
    }).json()


@app.route("/api/stream/stats/reset", methods=["POST"])
def reset_stream_stats():
    global stream_stats
    with stream_stats_lock:
        stream_stats["total_bytes"] = 0
        stream_stats["current_session_bytes"] = 0
        stream_stats["start_time"] = time.time()
    return Result.ok().json()


@app.route("/api/mpd/<bvid>", methods=["GET"])
def get_mpd(bvid: str):
    global current_video_info, current_video_stream_info, current_audio_info
    
    if not current_video_stream_info or not current_audio_info:
        return Result.bad_request("No stream loaded")
    
    duration_ms = current_video_info.duration * 1000
    video_url = f"http://localhost:{Server.PORT}/api/stream/video/{bvid}"
    audio_url = f"http://localhost:{Server.PORT}/api/stream/audio/{bvid}"
    
    video_init_range = current_video_stream_info.init_range
    video_index_range = current_video_stream_info.index_range
    audio_init_range = current_audio_info.init_range
    audio_index_range = current_audio_info.index_range
    
    print(f"[MPD] Video ranges: init={video_init_range}, index={video_index_range}")
    print(f"[MPD] Audio ranges: init={audio_init_range}, index={audio_index_range}")
    
    if not video_init_range or not video_index_range:
        print(f"[MPD Error] Missing video ranges: init={video_init_range}, index={video_index_range}")
        return Result.bad_request("无法获取视频索引范围，请尝试其他视频")
    
    if not audio_init_range or not audio_index_range:
        print(f"[MPD Error] Missing audio ranges: init={audio_init_range}, index={audio_index_range}")
        return Result.bad_request("无法获取音频索引范围，请尝试其他视频")
    
    print(f"[MPD] Using ranges -> Video: init={video_init_range}, index={video_index_range}")
    print(f"[MPD] Using ranges -> Audio: init={audio_init_range}, index={audio_index_range}")
    print(f"[MPD] Video bitrate: {current_video_stream_info.bitrate}, Audio bitrate: {current_audio_info.bitrate}")
    
    video_codecs = current_video_stream_info.codecs or "avc1.64001f"
    audio_codecs = current_audio_info.codecs or "mp4a.40.2"
    
    mpd_content = f'''<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" minBufferTime="PT1.5S" type="static" mediaPresentationDuration="PT{duration_ms/1000}S">
  <Period duration="PT{duration_ms/1000}S">
    <AdaptationSet mimeType="video/mp4" contentType="video" segmentAlignment="true" startWithSAP="1">
      <Representation id="video" bandwidth="{current_video_stream_info.bitrate}" width="{current_video_stream_info.width}" height="{current_video_stream_info.height}" codecs="{video_codecs}">
        <BaseURL>{video_url}</BaseURL>
        <SegmentBase indexRange="{video_index_range}">
          <Initialization range="{video_init_range}"/>
        </SegmentBase>
      </Representation>
    </AdaptationSet>
    <AdaptationSet mimeType="audio/mp4" contentType="audio" segmentAlignment="true" startWithSAP="1">
      <Representation id="audio" bandwidth="{current_audio_info.bitrate}" audioSamplingRate="{current_audio_info.sample_rate}" codecs="{audio_codecs}">
        <BaseURL>{audio_url}</BaseURL>
        <SegmentBase indexRange="{audio_index_range}">
          <Initialization range="{audio_init_range}"/>
        </SegmentBase>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>'''
    
    response = Response(mpd_content, mimetype="application/dash+xml")
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit("connected", {"message": "Connected to server"})


@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")


@socketio.on("play_video")
def handle_play_video(data):
    global current_video_info, current_audio_info, current_video_stream_info, current_danmaku_list, stream_stats

    print(f"[play_video] 收到播放请求: {data}")
    input_str = data.get("input", "")
    if not input_str:
        print("[play_video] 错误: 输入为空")
        emit("error", {"message": ErrorMessage.INPUT_EMPTY})
        return

    try:
        bvid = BilibiliAPI.parse_input(input_str)
        print(f"[play_video] 解析BV号: {bvid}")
        if not bvid:
            emit("error", {"message": ErrorMessage.INVALID_INPUT})
            return

        emit("status", {"message": "正在获取视频信息..."})

        current_video_info = bilibili_api.get_video_info(bvid)
        print(f"[play_video] 获取视频信息成功: {current_video_info.title}")
        
        current_audio_info = bilibili_api.get_audio_stream(bvid, current_video_info.cid)
        print(f"[play_video] 获取音频流成功")
        
        current_video_stream_info = bilibili_api.get_video_stream(bvid, current_video_info.cid)
        print(f"[play_video] 获取视频流成功")
        
        current_danmaku_list = bilibili_api.get_danmaku(bvid, current_video_info.cid)
        print(f"[play_video] 获取弹幕成功: {len(current_danmaku_list)}条")

        with stream_stats_lock:
            stream_stats["current_session_bytes"] = 0
            stream_stats["start_time"] = time.time()

        emit(
            "video_info",
            {
                "bvid": current_video_info.bvid,
                "title": current_video_info.title,
                "duration": current_video_info.duration,
                "owner": current_video_info.owner,
                "cover": current_video_info.cover,
                "view_count": current_video_info.view_count,
                "danmaku_count": current_video_info.danmaku_count,
            },
        )

        emit("status", {"message": "正在启动播放..."})

        audio_proxy_url = Server.proxy_url(bvid) + "/audio"
        video_proxy_url = Server.proxy_url(bvid) + "/video"
        
        emit(
            "audio_stream",
            {
                "url": audio_proxy_url,
                "duration": current_audio_info.duration,
                "bitrate": current_audio_info.bitrate,
                "sample_rate": current_audio_info.sample_rate,
                "channels": current_audio_info.channels,
            },
        )
        
        emit(
            "video_stream",
            {
                "url": current_video_stream_info.url,
                "proxy_url": video_proxy_url,
                "duration": current_video_stream_info.duration,
                "width": current_video_stream_info.width,
                "height": current_video_stream_info.height,
                "bitrate": current_video_stream_info.bitrate,
                "mime_type": current_video_stream_info.mime_type,
                "mpd_url": f"http://localhost:{Server.PORT}/api/mpd/{bvid}",
            },
        )
        
        emit(
            "danmaku_data",
            {
                "count": len(current_danmaku_list),
                "danmaku": [
                    {
                        "time": d.time,
                        "type": d.type,
                        "color": d.color,
                        "content": d.content,
                        "font_size": d.font_size,
                    }
                    for d in current_danmaku_list
                ],
            },
        )
        
        print(f"[play_video] 已发送代理URL: audio={audio_proxy_url}, video={video_proxy_url}")

    except APIError as e:
        print(f"[play_video] API错误: {e}")
        emit("error", {"message": f"API错误: {e.message}"})
    except Exception as e:
        print(f"[play_video] 异常: {e}")
        import traceback
        traceback.print_exc()
        emit("error", {"message": f"{ErrorMessage.PLAYBACK_FAILED}: {str(e)}"})


@socketio.on("get_comments")
def handle_get_comments(data):
    oid = data.get("oid", 0)
    page = data.get("page", 1)
    sort = data.get("sort", 2)
    bvid = data.get("bvid", "")
    
    try:
        comment_data = bilibili_api.get_comments(bvid, oid, page, sort)
        emit("comments_data", comment_data)
    except APIError as e:
        emit("error", {"message": e.message})
    except Exception as e:
        emit("error", {"message": str(e)})


@socketio.on("pause")
def handle_pause():
    emit("status", {"message": "已暂停"})


@socketio.on("resume")
def handle_resume():
    emit("status", {"message": "已恢复播放"})


@socketio.on("stop")
def handle_stop():
    global current_video_info, current_audio_info, current_video_stream_info, current_danmaku_list

    current_video_info = None
    current_audio_info = None
    current_video_stream_info = None
    current_danmaku_list = []

    emit("status", {"message": "已停止播放"})


@socketio.on("seek")
def handle_seek(data):
    time_seconds = data.get("time", 0)
    emit("status", {"message": f"已跳转到 {time_seconds:.1f}秒"})


@socketio.on("get_status")
def handle_get_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
    }

    if current_video_info:
        status["video_info"] = {
            "bvid": current_video_info.bvid,
            "title": current_video_info.title,
            "duration": current_video_info.duration,
        }

    emit("player_status", status)


if __name__ == "__main__":
    print("=" * 60)
    print("B站弹幕播放器后端服务")
    print("=" * 60)
    print(f"启动HTTP服务器: http://localhost:{Server.PORT}")
    print("WebSocket服务已启用")
    print("=" * 60)

    socketio.run(app, host=Server.HOST, port=Server.PORT, debug=Server.DEBUG, allow_unsafe_werkzeug=True)
