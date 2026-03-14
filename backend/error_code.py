class ErrorMessage:
    INPUT_EMPTY = "输入不能为空"
    INVALID_INPUT = "无效的输入格式"
    NO_AUDIO_LOADED = "没有加载音频"
    PLAYBACK_FAILED = "播放失败"
    VIDEO_NOT_FOUND = "视频不存在"
    NETWORK_ERROR = "网络错误"
    API_ERROR = "API错误"
    NO_DASH_STREAM = "没有DASH流"
    NO_AUDIO_STREAM = "没有音频流"
    REQUEST_TIMEOUT = "请求超时"
    NO_VIDEO_STREAM = "没有视频流"
    DANMAKU_ERROR = "弹幕获取失败"
    COMMENT_ERROR = "评论获取失败"


class APIError(Exception):
    def __init__(self, message: str, code: int = -1):
        self.message = message
        self.code = code
        super().__init__(self.message)

    @classmethod
    def invalid_bvid(cls, bvid: str):
        return cls(f"无效的BV号: {bvid}", code=-400)

    @classmethod
    def video_not_found(cls, bvid: str):
        return cls(f"视频不存在: {bvid}", code=-404)

    @classmethod
    def request_timeout(cls, bvid: str):
        return cls(f"请求超时: {bvid}", code=-504)

    @classmethod
    def network_error(cls, error: str):
        return cls(f"网络错误: {error}", code=-500)

    @classmethod
    def api_error(cls, message: str):
        return cls(message, code=-500)

    @classmethod
    def no_dash_stream(cls):
        return cls(ErrorMessage.NO_DASH_STREAM, code=-500)

    @classmethod
    def no_audio_stream(cls):
        return cls(ErrorMessage.NO_AUDIO_STREAM, code=-500)

    @classmethod
    def no_video_stream(cls):
        return cls(ErrorMessage.NO_VIDEO_STREAM, code=-500)

    @classmethod
    def danmaku_error(cls, message: str):
        return cls(f"{ErrorMessage.DANMAKU_ERROR}: {message}", code=-500)

    @classmethod
    def comment_error(cls, message: str):
        return cls(f"{ErrorMessage.COMMENT_ERROR}: {message}", code=-500)
