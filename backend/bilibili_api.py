import requests
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from constant import HttpHeader, BilibiliAPI as APIConst
from error_code import APIError


@dataclass
class VideoInfo:
    bvid: str
    cid: int
    title: str
    duration: int
    owner: str
    cover: str
    view_count: int = 0
    danmaku_count: int = 0


@dataclass
class VideoStreamInfo:
    url: str
    backup_urls: List[str]
    duration: int
    width: int
    height: int
    bitrate: int
    mime_type: str
    codecs: str
    init_range: str
    index_range: str


@dataclass
class AudioStreamInfo:
    url: str
    backup_urls: List[str]
    duration: int
    bitrate: int
    sample_rate: int
    channels: int
    codecs: str
    init_range: str
    index_range: str


@dataclass
class DanmakuInfo:
    time: float
    type: int
    color: int
    content: str
    font_size: int = 25


@dataclass
class CommentInfo:
    rpid: int
    oid: int
    type: int
    mid: int
    root: int
    parent: int
    dialog: int
    count: int
    rcount: int
    like: int
    ctime: int
    member: Dict[str, Any]
    content: Dict[str, Any]
    replies: List["CommentInfo"] = field(default_factory=list)


class BilibiliAPI:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HttpHeader.default_headers())

    @staticmethod
    def is_valid_bvid(bvid: str) -> bool:
        return bool(APIConst.BV_PATTERN.match(bvid))

    @staticmethod
    def extract_bvid(url: str) -> Optional[str]:
        match = APIConst.URL_PATTERN.search(url)
        return match.group(3) if match else None

    @staticmethod
    def parse_input(input_str: str) -> Optional[str]:
        input_str = input_str.strip()
        if BilibiliAPI.is_valid_bvid(input_str):
            return input_str.upper()

        bvid = BilibiliAPI.extract_bvid(input_str)
        if bvid:
            return bvid

        return None

    def get_video_info(self, bvid: str) -> VideoInfo:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        params = {"bvid": bvid}
        headers = HttpHeader.video_headers(bvid)

        try:
            response = self.session.get(
                APIConst.VIDEO_INFO_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                if data.get("code") == -400:
                    raise APIError.video_not_found(bvid)
                raise APIError.api_error(error_msg)

            video_data = data.get("data", {})
            stat = video_data.get("stat", {})
            return VideoInfo(
                bvid=video_data.get("bvid", bvid),
                cid=video_data.get("cid", 0),
                title=video_data.get("title", ""),
                duration=video_data.get("duration", 0),
                owner=video_data.get("owner", {}).get("name", ""),
                cover=video_data.get("pic", ""),
                view_count=stat.get("view", 0),
                danmaku_count=stat.get("danmaku", 0),
            )

        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.RequestException as e:
            raise APIError.network_error(str(e))

    def get_video_stream(self, bvid: str, cid: int, quality: int = 80) -> VideoStreamInfo:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        # 优先获取DASH格式
        # fnval标志位: 16(DASH) | 64(需要segmentBase) | 128(4K) | 256(需要HDR) | 512(需要杜比音频) | 1024(需要杜比视界)
        params_dash = {
            "bvid": bvid,
            "cid": cid,
            "qn": quality,
            "fnval": 16 | 64 | 128,  # DASH格式 + segmentBase + 4K
            "fnver": 0,
            "fourk": 1,
        }

        headers = HttpHeader.video_headers(bvid)

        try:
            response = self.session.get(
                APIConst.PLAY_URL,
                params=params_dash,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                raise APIError.api_error(error_msg)

            play_data = data.get("data", {})

            # 优先使用DASH格式
            if "dash" in play_data:
                video_streams = play_data.get("dash", {}).get("video", [])
                if video_streams:
                    video_stream = video_streams[0]
                    
                    print(f"[get_video_stream] video_stream keys: {list(video_stream.keys())}")
                    
                    codecid = video_stream.get("codecid", 7)
                    if codecid == 7:
                        codecs = "avc1.64001f"
                    elif codecid == 12:
                        codecs = "hev1.1.6.L120.90"
                    elif codecid == 13:
                        codecs = "av01.0.04M.08"
                    else:
                        codecs = "avc1.64001f"
                    
                    segment_base = video_stream.get("segmentBase") or video_stream.get("segment_base") or {}
                    
                    init_range = segment_base.get("initialization") or segment_base.get("Initialization") or ""
                    index_range = (segment_base.get("index_range") or 
                                   segment_base.get("indexRange") or 
                                   segment_base.get("IndexRange") or "")
                    
                    print(f"[get_video_stream] 使用DASH格式: {video_stream.get('baseUrl', '')[:80]}...")
                    print(f"[get_video_stream] codecid={codecid}, codecs={codecs}")
                    print(f"[get_video_stream] segmentBase={segment_base}")
                    print(f"[get_video_stream] init_range={init_range}, index_range={index_range}")
                    
                    return VideoStreamInfo(
                        url=video_stream.get("baseUrl", "") or video_stream.get("base_url", ""),
                        backup_urls=video_stream.get("backupUrl", []) or video_stream.get("backup_url", []),
                        duration=play_data.get("timelength", 0) // 1000,
                        width=video_stream.get("width", 1920),
                        height=video_stream.get("height", 1080),
                        bitrate=video_stream.get("bandwidth", 0),
                        mime_type=video_stream.get("mimeType", "") or video_stream.get("mime_type", "video/mp4"),
                        codecs=codecs,
                        init_range=init_range,
                        index_range=index_range,
                    )

            # 如果没有DASH，尝试FLV格式
            print("[get_video_stream] DASH不可用，尝试FLV格式")
            params_flv = {
                "bvid": bvid,
                "cid": cid,
                "qn": quality,
                "fnval": 0,
                "fnver": 0,
                "fourk": 0,
            }
            
            response = self.session.get(
                APIConst.PLAY_URL,
                params=params_flv,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise APIError.api_error(data.get("message", "Unknown error"))
                
            play_data = data.get("data", {})
            
            if "durl" in play_data and play_data["durl"]:
                video_url = play_data["durl"][0].get("url", "")
                print(f"[get_video_stream] 使用FLV格式: {video_url[:80]}...")
                return VideoStreamInfo(
                    url=video_url,
                    backup_urls=[d.get("url", "") for d in play_data.get("durl", [])[1:]],
                    duration=play_data.get("timelength", 0) // 1000,
                    width=1920,
                    height=1080,
                    bitrate=0,
                    mime_type="video/flv",
                    codecs="",
                    init_range="",
                    index_range="",
                )

            raise APIError.no_video_stream()

        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.RequestException as e:
            raise APIError.network_error(str(e))

    def get_audio_stream(self, bvid: str, cid: int, quality: int = 30280) -> AudioStreamInfo:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": 16,
            "fnval": 16 | 64 | 128,  # DASH格式 + segmentBase + 4K
            "fnver": 0,
            "fourk": 0,
        }

        headers = HttpHeader.video_headers(bvid)

        try:
            response = self.session.get(
                APIConst.PLAY_URL,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                raise APIError.api_error(error_msg)

            play_data = data.get("data", {})

            if "dash" not in play_data:
                raise APIError.no_dash_stream()

            audio_streams = play_data.get("dash", {}).get("audio", [])
            if not audio_streams:
                raise APIError.no_audio_stream()

            audio_stream = audio_streams[0]
            
            print(f"[get_audio_stream] audio_stream keys: {list(audio_stream.keys())}")
            
            audio_codecid = audio_stream.get("codecid", 0)
            if audio_codecid == 0:
                audio_codecs = "mp4a.40.2"
            else:
                audio_codecs = "mp4a.40.2"
            
            audio_segment_base = audio_stream.get("segmentBase") or audio_stream.get("segment_base") or {}
            audio_init_range = audio_segment_base.get("initialization") or audio_segment_base.get("Initialization") or ""
            audio_index_range = (audio_segment_base.get("index_range") or 
                                 audio_segment_base.get("indexRange") or 
                                 audio_segment_base.get("IndexRange") or "")
            
            print(f"[get_audio_stream] audio_codecid={audio_codecid}, codecs={audio_codecs}")
            print(f"[get_audio_stream] segmentBase={audio_segment_base}")
            print(f"[get_audio_stream] init_range={audio_init_range}, index_range={audio_index_range}")

            return AudioStreamInfo(
                url=audio_stream.get("baseUrl", "") or audio_stream.get("base_url", ""),
                backup_urls=audio_stream.get("backupUrl", []) or audio_stream.get("backup_url", []),
                duration=play_data.get("timelength", 0) // 1000,
                bitrate=audio_stream.get("bandwidth", 0),
                sample_rate=audio_stream.get("sampleRate", 44100),
                channels=audio_stream.get("channel", 2),
                codecs=audio_codecs,
                init_range=audio_init_range,
                index_range=audio_index_range,
            )

        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.RequestException as e:
            raise APIError.network_error(str(e))

    def get_danmaku(self, bvid: str, cid: int) -> List[DanmakuInfo]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        headers = HttpHeader.video_headers(bvid)

        try:
            # 尝试获取XML格式的弹幕
            response = self.session.get(
                f"https://api.bilibili.com/x/v1/dm/list.so",
                params={"oid": cid},
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                return []

            danmaku_list = self._parse_danmaku_xml(response.content)
            return danmaku_list

        except requests.RequestException as e:
            raise APIError.danmaku_error(str(e))

    def _parse_danmaku_xml(self, content: bytes) -> List[DanmakuInfo]:
        danmaku_list = []
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content.decode("utf-8", errors="ignore"))
            for d in root.findall(".//d"):
                p_attr = d.get("p", "")
                if p_attr:
                    parts = p_attr.split(",")
                    if len(parts) >= 8:
                        danmaku = DanmakuInfo(
                            time=float(parts[0]),
                            type=int(parts[1]),
                            color=int(parts[3]),
                            content=d.text or "",
                            font_size=int(parts[2]),
                        )
                        danmaku_list.append(danmaku)
        except Exception as e:
            print(f"解析弹幕失败: {e}")
        return danmaku_list

    def get_comments(self, bvid: str, oid: int, page: int = 1, sort: int = 2) -> Dict[str, Any]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        headers = HttpHeader.video_headers(bvid)

        try:
            response = self.session.get(
                "https://api.bilibili.com/x/v2/reply",
                params={
                    "type": 1,
                    "oid": oid,
                    "pn": page,
                    "sort": sort,
                },
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError.comment_error(data.get("message", "Unknown error"))

            return data.get("data", {})

        except requests.RequestException as e:
            raise APIError.comment_error(str(e))

    def get_video_with_audio(self, input_str: str) -> tuple:
        bvid = self.parse_input(input_str)
        if not bvid:
            raise ValueError(f"Cannot parse BVID from input: {input_str}")

        video_info = self.get_video_info(bvid)
        audio_stream = self.get_audio_stream(bvid, video_info.cid)

        return video_info, audio_stream

    def close(self):
        self.session.close()


bilibili_api = BilibiliAPI()
