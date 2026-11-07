/**
 * 遥控 · 语音输入模块（独立）
 * 使用浏览器 Web Speech API，无需申请阿里/讯飞等 SDK。
 * 不读写 textarea；只通过回调吐出识别文本（由页面接到文字模块或直接提交）。
 *
 * 用法：
 *   const voice = AgentTaskVoiceInput.mount({
 *     buttonId: "voiceHold",
 *     statusId: "voiceStatus",
 *     onPartial: (t) => {},
 *     onFinal: (t) => {},
 *     onError: (msg) => {},
 *   });
 *
 * 模式：
 *   - hold（默认，阶段 B）：按住说话，松开结束并出最终句
 *   - continuous（阶段 A）：点一下开麦持续听，再点停止；停顿出句走 onFinal
 */
(function (global) {
  "use strict";

  function SpeechCtor() {
    return global.SpeechRecognition || global.webkitSpeechRecognition || null;
  }

  function pickLang() {
    // Android Chrome 对 zh-CN 偶发不认；优先 cmn-Hans-CN，再 zh-CN / zh
    const ua = String(navigator.userAgent || "");
    if (/Android/i.test(ua)) return "cmn-Hans-CN";
    return "zh-CN";
  }

  function isAvailable() {
    return !!SpeechCtor();
  }

  function mount(opts) {
    opts = opts || {};
    const btn = document.getElementById(opts.buttonId || "voiceHold");
    const statusEl = document.getElementById(opts.statusId || "voiceStatus");
    const onPartial = typeof opts.onPartial === "function" ? opts.onPartial : function () {};
    const onFinal = typeof opts.onFinal === "function" ? opts.onFinal : function () {};
    const onError = typeof opts.onError === "function" ? opts.onError : function () {};
    const onState = typeof opts.onState === "function" ? opts.onState : function () {};

    if (!btn) {
      throw new Error("AgentTaskVoiceInput: missing button");
    }

    let mode = opts.mode === "continuous" ? "continuous" : "hold";
    let rec = null;
    let listening = false;
    let wantListen = false;
    let lastFinal = "";
    let restartTimer = null;

    function setStatus(msg) {
      if (statusEl) statusEl.textContent = msg || "";
    }

    function setListeningUi(on) {
      listening = !!on;
      btn.classList.toggle("is-listening", listening);
      btn.setAttribute("aria-pressed", listening ? "true" : "false");
      if (mode === "hold") {
        btn.textContent = listening ? "松开结束" : "按住说话";
      } else {
        btn.textContent = listening ? "停止连麦" : "开始连麦";
      }
      onState({ listening: listening, mode: mode });
    }

    function destroyRec() {
      if (restartTimer) {
        clearTimeout(restartTimer);
        restartTimer = null;
      }
      if (!rec) return;
      try {
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
        rec.abort();
      } catch (_) {}
      rec = null;
    }

    function emitFinal(text) {
      const t = String(text || "").trim();
      if (!t) return;
      lastFinal = t;
      onFinal(t);
    }

    function makeRec() {
      const Ctor = SpeechCtor();
      if (!Ctor) {
        onError("当前浏览器不支持语音识别（请用手机 Chrome）");
        setStatus("不支持语音：请用 Chrome");
        return null;
      }
      const r = new Ctor();
      r.lang = opts.lang || pickLang();
      r.interimResults = true;
      r.maxAlternatives = 1;
      r.continuous = mode === "continuous";

      r.onstart = function () {
        setListeningUi(true);
        setStatus(mode === "continuous" ? "连麦中… 说完一句会自动出字" : "正在听…");
      };

      r.onresult = function (ev) {
        let interim = "";
        let finals = [];
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const row = ev.results[i];
          const piece = (row[0] && row[0].transcript) || "";
          if (row.isFinal) finals.push(piece);
          else interim += piece;
        }
        if (interim) {
          onPartial(interim);
          setStatus("识别中：" + interim);
        }
        if (finals.length) {
          const joined = finals.join("").trim();
          if (joined) {
            emitFinal(joined);
            setStatus("已识别：" + joined);
          }
        }
      };

      r.onerror = function (ev) {
        const code = (ev && ev.error) || "error";
        if (code === "aborted" || code === "no-speech") {
          // 松开/静音属正常
          return;
        }
        if (code === "not-allowed" || code === "service-not-allowed") {
          onError("麦克风权限被拒绝，请在浏览器设置里允许");
          setStatus("需要麦克风权限");
          wantListen = false;
          setListeningUi(false);
          return;
        }
        if (code === "network") {
          onError("语音服务网络异常（Web Speech 依赖系统/Google 服务）");
          setStatus("网络异常，稍后重试");
          return;
        }
        onError("语音识别：" + code);
        setStatus("识别出错：" + code);
      };

      r.onend = function () {
        setListeningUi(false);
        // continuous：用户仍要听 → 自动续开（浏览器常在一小段后自行 end）
        if (wantListen && mode === "continuous") {
          restartTimer = setTimeout(function () {
            if (!wantListen) return;
            startListen();
          }, 280);
          setStatus("连麦续听中…");
          return;
        }
        if (!lastFinal) setStatus(mode === "hold" ? "按住说话，松开填入文字" : "已停止连麦");
      };

      return r;
    }

    function startListen() {
      destroyRec();
      rec = makeRec();
      if (!rec) return;
      try {
        rec.start();
      } catch (e) {
        onError(String(e && e.message ? e.message : e));
        setStatus("无法启动麦克风");
        wantListen = false;
        setListeningUi(false);
      }
    }

    function stopListen() {
      wantListen = false;
      if (restartTimer) {
        clearTimeout(restartTimer);
        restartTimer = null;
      }
      if (!rec) {
        setListeningUi(false);
        return;
      }
      try {
        rec.stop();
      } catch (_) {
        try {
          rec.abort();
        } catch (__) {}
        setListeningUi(false);
      }
    }

    function bindHold() {
      const startEv = function (ev) {
        if (ev.cancelable) ev.preventDefault();
        wantListen = true;
        lastFinal = "";
        startListen();
      };
      const endEv = function (ev) {
        if (ev && ev.cancelable) ev.preventDefault();
        stopListen();
      };
      btn.addEventListener("pointerdown", startEv);
      btn.addEventListener("pointerup", endEv);
      btn.addEventListener("pointercancel", endEv);
      btn.addEventListener("pointerleave", function (ev) {
        if (listening) endEv(ev);
      });
      // 防止长按弹出系统菜单
      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
      });
    }

    function bindToggle() {
      btn.addEventListener("click", function () {
        if (listening || wantListen) {
          stopListen();
          setStatus("已停止连麦");
        } else {
          wantListen = true;
          lastFinal = "";
          startListen();
        }
      });
    }

    function setMode(next) {
      const m = next === "continuous" ? "continuous" : "hold";
      if (m === mode) return;
      stopListen();
      mode = m;
      setListeningUi(false);
      setStatus(
        mode === "continuous"
          ? "连麦模式：点开始，说完一句自动出字"
          : "按住说话，松开填入文字"
      );
      // 换模式后按钮文案
      btn.textContent = mode === "continuous" ? "开始连麦" : "按住说话";
    }

    if (!isAvailable()) {
      btn.disabled = true;
      setStatus("本浏览器不支持语音（建议手机 Chrome）");
      onError("unsupported");
    } else if (mode === "continuous") {
      bindToggle();
      btn.textContent = "开始连麦";
      setStatus("连麦模式：点开始，说完一句自动出字");
    } else {
      bindHold();
      btn.textContent = "按住说话";
      setStatus("按住说话，松开填入文字（无需申请 SDK）");
    }

    return {
      kind: "voice",
      isAvailable: isAvailable,
      setMode: setMode,
      getMode: function () {
        return mode;
      },
      start: function () {
        wantListen = true;
        startListen();
      },
      stop: stopListen,
      isListening: function () {
        return listening;
      },
    };
  }

  global.AgentTaskVoiceInput = {
    mount: mount,
    isAvailable: isAvailable,
  };
})(typeof window !== "undefined" ? window : this);
