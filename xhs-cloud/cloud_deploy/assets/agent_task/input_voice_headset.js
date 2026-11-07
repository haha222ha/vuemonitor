/**
 * 遥控 · 蓝牙耳机媒体键桥接（独立）
 *
 * 原理与音乐 App 相同：
 *   1) 页面声明 Media Session（标题/封面/播放状态）
 *   2) 播放一段近乎无声音频，让系统把「当前媒体」交给本页
 *   3) 耳机播放/暂停键 → navigator.mediaSession play/pause
 *   4) 回调里切换语音识别 start/stop
 *
 * 限制（调研结论）：
 *   - 需先在页面上点一次「启用耳机键」（浏览器手势策略）
 *   - Chrome Android 最稳；微信内置浏览器常无效
 *   - 多数蓝牙耳机只有一颗播放/暂停，适合「再按一次 = 切换」
 *   - 专业工牌麦才走 WebHID；普通耳机不要走 HID
 */
(function (global) {
  "use strict";

  function isAvailable() {
    return !!(global.navigator && navigator.mediaSession && typeof navigator.mediaSession.setActionHandler === "function");
  }

  /**
   * 1 秒近静音 WAV（base64），循环播放占住媒体会话。
   * 音量极低，避免吵；部分机型要求非完全静音才算「在播」。
   */
  function silentLoopUrl() {
    // 极短 PCM WAV，约 0.1s；浏览器会按 loop 续播
    var b64 =
      "UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=";
    return "data:audio/wav;base64," + b64;
  }

  function mount(opts) {
    opts = opts || {};
    var onToggle = typeof opts.onToggle === "function" ? opts.onToggle : function () {};
    var onError = typeof opts.onError === "function" ? opts.onError : function () {};
    var onState = typeof opts.onState === "function" ? opts.onState : function () {};
    var getListening =
      typeof opts.getListening === "function"
        ? opts.getListening
        : function () {
            return false;
          };
    var title = opts.title || "Cursor 遥控 · 语音输入";
    var artist = opts.artist || "点耳机播放键：开始/结束识别";

    if (!isAvailable()) {
      onError("unsupported");
      return {
        kind: "headset",
        isAvailable: function () {
          return false;
        },
        enable: function () {
          return Promise.resolve(false);
        },
        disable: function () {},
        isEnabled: function () {
          return false;
        },
      };
    }

    var audio = null;
    var enabled = false;
    var handlersBound = false;

    function setMeta(listening) {
      try {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: title,
          artist: listening ? "识别中 · 再按结束" : artist,
          album: "Agent Task",
        });
        navigator.mediaSession.playbackState = listening ? "playing" : "paused";
      } catch (_) {}
    }

    function ensureAudio() {
      if (audio) return audio;
      audio = new Audio();
      audio.src = silentLoopUrl();
      audio.loop = true;
      audio.preload = "auto";
      audio.volume = 0.01; // 极低音量，满足「在播」判定
      audio.setAttribute("playsinline", "true");
      return audio;
    }

    function bindHandlers() {
      if (handlersBound) return;
      handlersBound = true;
      var actions = ["play", "pause", "stop"];
      actions.forEach(function (action) {
        try {
          navigator.mediaSession.setActionHandler(action, function () {
            if (!enabled) return;
            // 耳机同一颗键：系统可能发 play 或 pause，统一当「切换」
            try {
              onToggle(action);
            } catch (e) {
              onError(String(e && e.message ? e.message : e));
            }
            // 切完后按实际识别态刷新锁屏/通知栏图标
            setTimeout(function () {
              setMeta(!!getListening());
              // 保持音频会话：识别中保持 playing；否则 paused 但仍占会话
              if (audio) {
                if (getListening()) {
                  audio.play().catch(function () {});
                } else {
                  // 不 pause 掉会话，否则下次耳机键可能丢；继续微声循环
                  audio.play().catch(function () {});
                  try {
                    navigator.mediaSession.playbackState = "paused";
                  } catch (_) {}
                }
              }
            }, 50);
          });
        } catch (e) {
          // 个别 action 不支持可忽略
        }
      });
    }

    function enable() {
      if (!isAvailable()) {
        onError("unsupported");
        return Promise.resolve(false);
      }
      bindHandlers();
      var a = ensureAudio();
      return a
        .play()
        .then(function () {
          enabled = true;
          setMeta(!!getListening());
          onState({ enabled: true });
          return true;
        })
        .catch(function (err) {
          enabled = false;
          onError("无法占用媒体会话：" + (err && err.message ? err.message : String(err)));
          onState({ enabled: false });
          return false;
        });
    }

    function disable() {
      enabled = false;
      try {
        if (audio) {
          audio.pause();
        }
        navigator.mediaSession.playbackState = "none";
        navigator.mediaSession.metadata = null;
      } catch (_) {}
      onState({ enabled: false });
    }

    function syncListening(listening) {
      if (!enabled) return;
      setMeta(!!listening);
    }

    return {
      kind: "headset",
      isAvailable: isAvailable,
      enable: enable,
      disable: disable,
      isEnabled: function () {
        return enabled;
      },
      syncListening: syncListening,
    };
  }

  global.AgentTaskVoiceHeadset = {
    mount: mount,
    isAvailable: isAvailable,
  };
})(typeof window !== "undefined" ? window : this);
