const CONFIG = {
  HOT_ZONE_EXPAND: { left: 100, right: 100, top: 50, bottom: 50 },
  VIDEO_CONTAINER_SIZE: { width: 600, height: 337 },
  MAX_DANMAKU: 200,
  DANMAKU_SPEED: 150,
  DANMAKU_GENERATE_INTERVAL: 500,
  BACKEND_URL: 'http://localhost:5000'
};

class DanmakuItem {
  constructor(text, color, fontSize, y, canvasWidth) {
    this.text = text;
    this.color = color;
    this.fontSize = fontSize;
    this.y = y;
    this.x = canvasWidth;
    this.speed = CONFIG.DANMAKU_SPEED + Math.random() * 50;
    this.baseSpeed = this.speed;
    this.width = 0;
    this.height = fontSize;
    this.isHovered = false;
    this.isSkewed = false;
    this.opacity = 1;
  }

  updateWidth(ctx) {
    ctx.font = `${this.fontSize}px "Microsoft YaHei", sans-serif`;
    this.width = ctx.measureText(this.text).width;
  }

  update(deltaTime) {
    if (this.isHovered) {
      this.speed = this.baseSpeed * 2;
    } else {
      this.speed = this.baseSpeed;
    }
    this.x -= this.speed * deltaTime;
  }

  draw(ctx) {
    ctx.save();
    if (this.isHovered && this.isSkewed) {
      ctx.transform(1, 0, -0.3, 1, 0, 0);
    }
    ctx.globalAlpha = this.opacity;
    ctx.font = `${this.fontSize}px "Microsoft YaHei", sans-serif`;
    ctx.fillStyle = this.color;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
    ctx.shadowBlur = 2;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 1;
    if (this.isHovered) {
      ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
      ctx.shadowBlur = 8;
    }
    ctx.fillText(this.text, this.x, this.y + this.fontSize);
    ctx.restore();
  }

  getBounds() {
    return { x: this.x, y: this.y, width: this.width, height: this.height };
  }

  isOffScreen() {
    return this.x + this.width < 0;
  }
}

class DanmakuSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.danmakuList = [];
    this.paused = false;
    this.lastTime = 0;
    this.danmakuQueue = [];
    this.lastGenerateTime = 0;
    this.videoContainerRect = null;
    this.hotZoneRect = null;
    this.mouseX = 0;
    this.mouseY = 0;
    this.isInHotZone = false;
    this.hoveredDanmaku = null;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  setVideoContainerRect(rect) {
    this.videoContainerRect = rect;
    this.updateHotZone();
  }

  updateHotZone() {
    if (this.videoContainerRect) {
      this.hotZoneRect = {
        x: this.videoContainerRect.x - CONFIG.HOT_ZONE_EXPAND.left,
        y: this.videoContainerRect.y - CONFIG.HOT_ZONE_EXPAND.top,
        width: this.videoContainerRect.width + CONFIG.HOT_ZONE_EXPAND.left + CONFIG.HOT_ZONE_EXPAND.right,
        height: this.videoContainerRect.height + CONFIG.HOT_ZONE_EXPAND.top + CONFIG.HOT_ZONE_EXPAND.bottom
      };
    }
  }

  isInVideoContainer(danmaku) {
    if (!this.videoContainerRect) return false;
    const bounds = danmaku.getBounds();
    return this.rectsIntersect(bounds, this.videoContainerRect);
  }

  rectsIntersect(rect1, rect2) {
    return !(rect1.x + rect1.width < rect2.x || rect1.x > rect2.x + rect2.width ||
      rect1.y + rect1.height < rect2.y || rect1.y > rect2.y + rect2.height);
  }

  isPointInRect(x, y, rect) {
    return x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height;
  }

  updateMousePosition(x, y) {
    this.mouseX = x;
    this.mouseY = y;
    if (this.hotZoneRect) {
      this.isInHotZone = this.isPointInRect(x, y, this.hotZoneRect);
    }
    if (this.hoveredDanmaku) {
      this.hoveredDanmaku.isHovered = false;
      this.hoveredDanmaku.isSkewed = false;
      this.hoveredDanmaku = null;
    }
    if (this.isInHotZone) {
      for (const danmaku of this.danmakuList) {
        const bounds = danmaku.getBounds();
        if (this.isPointInRect(x, y, bounds)) {
          danmaku.isHovered = true;
          danmaku.isSkewed = true;
          this.hoveredDanmaku = danmaku;
          break;
        }
      }
    }
  }

  addDanmaku(text, color, fontSize) {
    if (this.danmakuList.length >= CONFIG.MAX_DANMAKU) return;
    const y = Math.random() * (this.canvas.height - 100) + 20;
    const danmaku = new DanmakuItem(text, color, fontSize, y, this.canvas.width);
    danmaku.updateWidth(this.ctx);
    this.danmakuList.push(danmaku);
  }

  addDanmakuQueue(danmakuData) {
    this.danmakuQueue = danmakuData.map(d => ({
      time: d.time,
      text: d.content,
      color: `#${d.color.toString(16).padStart(6, '0')}`,
      fontSize: d.font_size || 25
    }));
  }

  generateMockDanmaku() {
    const mockTexts = ['哈哈哈哈哈哈', '太强了', '前方高能', '泪目', 'awsl', '这波操作666', '笑死我了', '太真实了', '爷青回', '绝了'];
    const colors = ['#ffffff', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9'];
    const text = mockTexts[Math.floor(Math.random() * mockTexts.length)];
    const color = colors[Math.floor(Math.random() * colors.length)];
    const fontSize = 20 + Math.floor(Math.random() * 15);
    this.addDanmaku(text, color, fontSize);
  }

  update(currentTime, videoTime) {
    if (this.paused) return;
    const deltaTime = (currentTime - this.lastTime) / 1000;
    this.lastTime = currentTime;
    if (currentTime - this.lastGenerateTime > CONFIG.DANMAKU_GENERATE_INTERVAL) {
      if (this.danmakuQueue.length > 0) {
        const matchingDanmaku = this.danmakuQueue.filter(d => Math.abs(d.time - videoTime) < 0.5);
        matchingDanmaku.forEach(d => this.addDanmaku(d.text, d.color, d.fontSize));
      } else {
        this.generateMockDanmaku();
      }
      this.lastGenerateTime = currentTime;
    }
    for (let i = this.danmakuList.length - 1; i >= 0; i--) {
      const danmaku = this.danmakuList[i];
      danmaku.update(deltaTime);
      if (this.isInVideoContainer(danmaku)) {
        danmaku.opacity = 0;
      } else {
        danmaku.opacity = 1;
      }
      if (danmaku.isOffScreen()) {
        this.danmakuList.splice(i, 1);
      }
    }
  }

  draw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (const danmaku of this.danmakuList) {
      danmaku.draw(this.ctx);
    }
  }

  setPaused(paused) { this.paused = paused; }
  clear() { this.danmakuList = []; this.danmakuQueue = []; }
}

class VideoPlayer {
  constructor() {
    this.video = document.getElementById('video-player');
    this.container = document.getElementById('video-container');
    this.titleEl = document.getElementById('video-title');
    this.hls = null;
    this.flv = null;
    this.dash = null;
    this.currentBvid = null;
    this.isPlaying = false;
    this.videoUrl = null;
    this.audioUrl = null;
  }

  cleanup() {
    if (this.hls) { this.hls.destroy(); this.hls = null; }
    if (this.flv) { this.flv.destroy(); this.flv = null; }
    if (this.dash) {
      this.dash.destroy();
      this.dash = null;
    }
    if (this.video) { this.video.src = ''; this.video.load(); }
  }

  async playHLS(url) {
    this.cleanup();
    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
      this.hls = new Hls({ debug: false, enableWorker: true });
      this.hls.loadSource(url);
      this.hls.attachMedia(this.video);
      this.hls.on(Hls.Events.MANIFEST_PARSED, () => this.video.play().catch(e => console.log('Autoplay prevented:', e)));
      this.hls.on(Hls.Events.ERROR, (event, data) => { console.error('HLS error:', data); if (data.fatal) showStatus('HLS播放错误'); });
    } else if (this.video.canPlayType('application/vnd.apple.mpegurl')) {
      this.video.src = url;
      this.video.play().catch(e => console.log('Autoplay prevented:', e));
    }
  }

  playFLV(url) {
    this.cleanup();
    console.log('Playing FLV:', url);
    if (typeof flvjs !== 'undefined' && flvjs.isSupported()) {
      this.flv = flvjs.createPlayer({ type: 'flv', url: url, isLive: false, cors: true });
      this.flv.attachMediaElement(this.video);
      this.flv.load();
      this.flv.on(flvjs.Events.ERROR, (errType, errDetail, errInfo) => { console.error('FLV error:', errType, errDetail); showStatus('FLV播放错误'); });
      this.video.play().catch(e => { console.error('FLV play error:', e); showStatus('视频播放失败'); });
    } else {
      showStatus('浏览器不支持FLV');
    }
  }

  async playDASH(videoUrl, audioUrl) {
    this.cleanup();
    console.log('Playing DASH:', { videoUrl, audioUrl, bvid: this.currentBvid });

    if (typeof dashjs !== 'undefined') {
      await this.playWithDashJS();
    } else {
      showStatus('dash.js未加载，尝试直接播放');
      this.playDirect(videoUrl);
    }
  }

  async playWithDashJS() {
    const mpdUrl = `${CONFIG.BACKEND_URL}/api/mpd/${this.currentBvid}`;
    console.log('Using dash.js with MPD URL:', mpdUrl);

    try {
      this.dash = dashjs.MediaPlayer().create();

      this.dash.updateSettings({
        streaming: {
          buffer: {
            fastSwitchEnabled: true,
            bufferTimeAtTopQuality: 30,
            bufferTimeAtTopQualityLongForm: 60
          }
        }
      });

      this.dash.initialize(this.video, mpdUrl, true);

      this.dash.on(dashjs.MediaPlayer.events.ERROR, (e) => {
        console.error('DASH.js error:', e);
        if (e.error && e.error.code) {
          showStatus(`DASH播放错误: ${e.error.message || e.error.code}`);
        } else if (e.event && e.event.id) {
          showStatus(`DASH播放错误: ${e.event.id}`);
        } else {
          showStatus('DASH播放错误');
        }
      });

      this.dash.on(dashjs.MediaPlayer.events.STREAM_INITIALIZED, () => {
        console.log('DASH stream initialized');
        showStatus('DASH播放初始化成功');
      });

      this.dash.on(dashjs.MediaPlayer.events.PLAYBACK_STARTED, () => {
        console.log('DASH playback started');
        this.isPlaying = true;
      });

      this.dash.on(dashjs.MediaPlayer.events.PLAYBACK_ERROR, (e) => {
        console.error('DASH playback error:', e);
        showStatus('播放出错，请检查视频源');
      });

    } catch (e) {
      console.error('dash.js initialization error:', e);
      showStatus('dash.js初始化失败: ' + e.message);
    }
  }

  play(url, mimeType = '') {
    this.cleanup();
    console.log('Playing:', url, 'mimeType:', mimeType);

    if (url.includes('.flv') || mimeType === 'video/flv') {
      this.playFLV(url);
    } else if (this.currentBvid && mimeType && mimeType.includes('mp4')) {
      const videoUrl = `${CONFIG.BACKEND_URL}/api/stream/video/${this.currentBvid}`;
      const audioUrl = `${CONFIG.BACKEND_URL}/api/stream/audio/${this.currentBvid}`;
      this.playDASH(videoUrl, audioUrl);
    } else {
      this.video.src = url;
      this.video.load();
      this.video.play().catch(e => { console.error('Play error:', e); showStatus('视频播放失败'); });
    }
  }

  playDirect(url) {
    this.video.src = url;
    this.video.load();
    this.video.play().catch(e => { console.error('Direct play error:', e); showStatus('视频播放失败'); });
  }

  play() { if (this.video) { this.video.play(); this.isPlaying = true; } }
  pause() { if (this.video) { this.video.pause(); this.isPlaying = false; } }
  stop() { this.cleanup(); this.currentVideoInfo = null; this.isPlaying = false; this.titleEl.textContent = '输入BV号或视频链接开始播放'; }
  setTitle(title) { this.titleEl.textContent = title; }
  getCurrentTime() { return this.video ? this.video.currentTime : 0; }
  getContainerRect() { return this.container.getBoundingClientRect(); }
}

class CommentPanel {
  constructor() {
    this.panel = document.getElementById('comment-panel');
    this.list = document.getElementById('comment-list');
    this.closeBtn = document.getElementById('close-comment');
    this.commentBtn = document.getElementById('comment-btn');
    this.isOpen = false;
    this.currentOid = 0;
    this.currentBvid = '';
    this.closeBtn.addEventListener('click', () => this.hide());
    this.commentBtn.addEventListener('click', () => this.toggle());
  }

  show() { this.panel.classList.add('show'); this.isOpen = true; }
  hide() { this.panel.classList.remove('show'); this.isOpen = false; }
  toggle() { if (this.isOpen) this.hide(); else { this.show(); if (this.currentOid) this.loadComments(); } }
  setVideoInfo(oid, bvid) { this.currentOid = oid; this.currentBvid = bvid; }

  async loadComments() {
    this.list.innerHTML = '<div class="loading-spinner"></div>';
    try {
      const response = await fetch(`${CONFIG.BACKEND_URL}/api/comments/${this.currentOid}?bvid=${this.currentBvid}`);
      const result = await response.json();
      if (result.success && result.data && result.data.replies) {
        this.renderComments(result.data.replies);
      } else {
        this.list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 20px;">暂无评论</p>';
      }
    } catch (error) {
      console.error('加载评论失败:', error);
      this.list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 20px;">加载评论失败</p>';
    }
  }

  renderComments(comments) {
    if (!comments || comments.length === 0) {
      this.list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 20px;">暂无评论</p>';
      return;
    }
    this.list.innerHTML = comments.slice(0, 20).map(comment => `
      <div class="comment-item">
        <div class="comment-user">
          <img class="comment-avatar" src="${comment.member.avatar}" alt="${comment.member.uname}">
          <span class="comment-name">${comment.member.uname}</span>
          <span class="comment-time">${this.formatTime(comment.ctime)}</span>
        </div>
        <div class="comment-content">${comment.content.message}</div>
        <div class="comment-stats">
          <span class="comment-stat">👍 ${this.formatNumber(comment.like)}</span>
          <span class="comment-stat">💬 ${comment.rcount}</span>
        </div>
      </div>`).join('');
  }

  formatTime(timestamp) {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diff = now - date;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 2592000000) return `${Math.floor(diff / 86400000)}天前`;
    return `${date.getMonth() + 1}-${date.getDate()}`;
  }

  formatNumber(num) { return num >= 10000 ? (num / 10000).toFixed(1) + '万' : num; }
}

let danmakuSystem = null;
let videoPlayer = null;
let commentPanel = null;
let socket = null;
let animationId = null;

function showStatus(message) {
  const statusEl = document.getElementById('status-text');
  statusEl.textContent = message;
  statusEl.classList.add('show');
  setTimeout(() => statusEl.classList.remove('show'), 2000);
}

function initSocket() {
  socket = io(CONFIG.BACKEND_URL);
  socket.on('connect', () => console.log('Connected to backend'));

  socket.on('video_info', (data) => {
    videoPlayer.setTitle(data.title);
    videoPlayer.currentBvid = data.bvid;
    commentPanel.setVideoInfo(data.cid, data.bvid);
    showStatus(`正在播放: ${data.title}`);
  });

  socket.on('video_stream', (data) => {
    console.log('Video stream:', data);
    videoPlayer.videoUrl = data.url;

    if (data.mime_type && data.mime_type.includes('flv')) {
      console.log('Using FLV player');
      videoPlayer.playFLV(data.url);
    } else if (data.mpd_url || (data.mime_type && data.mime_type.includes('mp4'))) {
      console.log('Using DASH player');
      videoPlayer.playWithDashJS();
    } else {
      console.log('Using direct play');
      videoPlayer.playDirect(data.url);
    }
  });

  socket.on('audio_stream', (data) => {
    console.log('Audio stream:', data);
    videoPlayer.audioUrl = data.url;
  });

  socket.on('danmaku_data', (data) => {
    console.log(`Received ${data.count} danmaku`);
    if (data.count > 0) danmakuSystem.addDanmakuQueue(data.danmaku);
  });

  socket.on('comments_data', (data) => { if (data && data.replies) commentPanel.renderComments(data.replies); });
  socket.on('status', (data) => showStatus(data.message));
  socket.on('error', (data) => showStatus(`错误: ${data.message}`));
}

async function playVideo(input) {
  if (!input.trim()) { showStatus('请输入BV号或视频链接'); return; }
  showStatus('正在获取视频信息...');
  danmakuSystem.clear();
  socket.emit('play_video', { input: input.trim() });
}

function initEventListeners() {
  const playBtn = document.getElementById('play-btn');
  const videoInput = document.getElementById('video-input');
  const playPauseBtn = document.getElementById('play-pause-btn');
  const stopBtn = document.getElementById('stop-btn');
  const videoContainer = document.getElementById('video-container');
  const inputContainer = document.getElementById('input-container');
  const commentPanelEl = document.getElementById('comment-panel');
  const commentBtn = document.getElementById('comment-btn');

  const setupInteractiveElement = (element) => {
    if (!element) return;
    element.addEventListener('mouseenter', () => { console.log('Mouse entered'); if (window.electronAPI) window.electronAPI.disableMousePenetrate(); });
    element.addEventListener('mouseleave', () => { console.log('Mouse left'); if (window.electronAPI) window.electronAPI.enableMousePenetrate(); });
  };

  [videoContainer, inputContainer, commentPanelEl, commentBtn, playBtn, videoInput, playPauseBtn, stopBtn].forEach(setupInteractiveElement);

  playBtn.addEventListener('click', () => playVideo(videoInput.value));
  videoInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') playVideo(videoInput.value); });
  playPauseBtn.addEventListener('click', () => { if (videoPlayer.isPlaying) { videoPlayer.pause(); playPauseBtn.textContent = '▶'; } else { videoPlayer.play(); playPauseBtn.textContent = '⏸'; } });
  stopBtn.addEventListener('click', () => { videoPlayer.stop(); danmakuSystem.clear(); socket.emit('stop'); showStatus('已停止播放'); });
  document.addEventListener('mousemove', (e) => danmakuSystem.updateMousePosition(e.clientX, e.clientY));

  if (window.electronAPI) {
    window.electronAPI.onToggleDanmaku((paused) => { danmakuSystem.setPaused(paused); showStatus(paused ? '弹幕已暂停' : '弹幕已恢复'); });
    window.electronAPI.onChangeVideoSource(() => { videoInput.focus(); videoInput.select(); });
  }
}

function animate(currentTime) {
  const videoTime = videoPlayer.getCurrentTime();
  danmakuSystem.update(currentTime, videoTime);
  danmakuSystem.draw();
  animationId = requestAnimationFrame(animate);
}

function updateVideoContainerRect() {
  const rect = videoPlayer.getContainerRect();
  danmakuSystem.setVideoContainerRect(rect);
}

async function init() {
  const canvas = document.getElementById('danmaku-canvas');
  danmakuSystem = new DanmakuSystem(canvas);
  videoPlayer = new VideoPlayer();
  commentPanel = new CommentPanel();
  initSocket();
  initEventListeners();
  setTimeout(updateVideoContainerRect, 500);
  window.addEventListener('resize', updateVideoContainerRect);
  danmakuSystem.lastTime = performance.now();
  animate(performance.now());
}

document.addEventListener('DOMContentLoaded', init);
