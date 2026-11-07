/**
 * 遥控 · 语音输入模块（独立）
 * 浏览器 Web Speech API，无需申请 SDK。
 * 默认：点击「开始识别」→ 再说 → 再点「结束识别」写入文字。
 * 不直接改 textarea，只回调 onPartial / onFinal（由页面接到文字模块）。
 */
(function (global) {
  "use strict";

  function SpeechCtor() {
    return global.SpeechRecognition || global.webkitSpeechRecognition || null;
  }

  function pickLang() {
    var ua = String(navigator.userAgent || "");
    // Android Chrome：cmn-Hans-CN / zh 比 zh-CN 稳
    if (/Android/i.test(ua)) return "cmn-Hans-CN";
    return "zh-CN";
  }

  function isAvailable() {
    return !!SpeechCtor();
  }

  function mount(opts) {
    opts = opts || {};
    var btn = document.getElementById(opts.buttonId || "voiceHold");
    var statusEl = document.getElementById(opts.statusId || "voiceStatus");
    var onPartial = typeof opts.onPartial === "function" ? opts.onPartial : function () {};
    var onFinal = typeof opts.onFinal === "function" ? opts.onFinal : function () {};
    var onError = typeof opts.onError === "function" ? opts.onError : function () {};
    var onState = typeof opts.onState === "function" ? opts.onState : function () {};

    if (!btn) throw new Error("AgentTaskVoiceInput: missing button");

    // continuousMulti：结束后自动再开一轮（多句连说）；默认 false = 点一次说一段
    var multi = !!opts.continuousMulti;
    var rec = null;
    var listening = false;
    var wantListen = false;
    var sessionFinals = []; // 本轮已确认句
    var draftInterim = ""; // 本轮未确认草稿
    var flushed = false;
    var restartTimer = null;
    var gen = 0; // 防止旧 recognition 的 onend 干扰
    var langTry = 0;
    var langs = [opts.lang || pickLang(), "zh-CN", "zh", "cmn-Hans-CN"];

    function setStatus(msg) {
      if (statusEl) statusEl.textContent = msg || "";
    }

    function setListeningUi(on) {
      listening = !!on;
      btn.classList.toggle("is-listening", listening);
      btn.setAttribute("aria-pressed", listening ? "true" : "false");
      btn.textContent = listening ? "结束识别" : "开始识别";
      onState({ listening: listening, multi: multi });
    }

    function clearSession() {
      sessionFinals = [];
      draftInterim = "";
      flushed = false;
    }

    function combinedText() {
      var parts = sessionFinals.slice();
      var d = String(draftInterim || "").trim();
      if (d) parts.push(d);
      return parts.join("").replace(/\s+/g, " ").trim();
    }

    function flushToFinal(reason) {
      if (flushed) return "";
      var text = combinedText();
      flushed = true;
      draftInterim = "";
      if (!text) {
        setStatus(reason || "未识别到内容，请再说一次");
        return "";
      }
      try {
        onFinal(text);
      } catch (e) {
        onError(String(e && e.message ? e.message : e));
      }
      setStatus("已写入：" + text);
      return text;
    }

    function teardownRec(abort) {
      if (restartTimer) {
        clearTimeout(restartTimer);
        restartTimer = null;
      }
      if (!rec) return;
      var r = rec;
      rec = null;
      try {
        r.onresult = null;
        r.onerror = null;
        // 保留 onend 会乱；直接摘掉，由调用方决定是否 flush
        r.onend = null;
        r.onstart = null;
        if (abort) r.abort();
        else r.stop();
      } catch (_) {}
    }

    function makeRec(myGen) {
      var Ctor = SpeechCtor();
      if (!Ctor) {
        onError("当前浏览器不支持语音识别（请用手机 Chrome）");
        setStatus("不支持语音：请用 Chrome");
        return null;
      }
      var r = new Ctor();
      r.lang = langs[langTry % langs.length];
      r.interimResults = true;
      r.maxAlternatives = 1;
      // 点按一轮内允许多段；浏览器会自己 end，由 wantListen 决定是否续
      r.continuous = true;

      r.onstart = function () {
        if (myGen !== gen) return;
        setListeningUi(true);
        setStatus("识别中… 说完再点「结束识别」");
      };

      r.onresult = function (ev) {
        if (myGen !== gen) return;
        var interim = "";
        var i;
        for (i = ev.resultIndex; i < ev.results.length; i++) {
          var row = ev.results[i];
          var piece = (row[0] && row[0].transcript) || "";
          if (!piece) continue;
          if (row.isFinal) {
            sessionFinals.push(piece);
            draftInterim = "";
          } else {
            interim += piece;
          }
        }
        if (interim) draftInterim = interim;
        var live = combinedText();
        if (live) {
          onPartial(live);
          setStatus("识别中：" + live);
        }
      };

      r.onerror = function (ev) {
        if (myGen !== gen) return;
        var code = (ev && ev.error) || "error";
        if (code === "aborted") return;
        if (code === "no-speech") {
          setStatus("没听到声音，请靠近麦克风再说");
          return;
        }
        if (code === "not-allowed" || code === "service-not-allowed") {
          onError("麦克风权限被拒绝，请在浏览器设置里允许");
          setStatus("需要麦克风权限");
          wantListen = false;
          setListeningUi(false);
          return;
        }
        if (code === "language-not-supported") {
          langTry += 1;
          setStatus("切换识别语言重试…");
          return;
        }
        if (code === "network") {
          onError("语音服务网络异常");
          setStatus("网络异常（Web Speech 需能访问系统语音服务）");
          return;
        }
        onError("语音识别：" + code);
        setStatus("识别出错：" + code);
      };

      r.onend = function () {
        if (myGen !== gen) return;
        // 用户已点结束：把草稿一并写入（含仅有 interim、没有 isFinal 的情况）
        if (!wantListen) {
          setListeningUi(false);
          flushToFinal();
          return;
        }
        // 仍要听：自动续开（Chrome 常会中途 end）
        setListeningUi(true);
        restartTimer = setTimeout(function () {
          if (!wantListen || myGen !== gen) return;
          startListen(true);
        }, 220);
        setStatus("继续听… " + (combinedText() || ""));
      };

      return r;
    }

    function startListen(isRestart) {
      if (!isRestart) clearSession();
      gen += 1;
      var myGen = gen;
      teardownRec(true);
      rec = makeRec(myGen);
      if (!rec) return;
      try {
        rec.start();
      } catch (e) {
        // InvalidStateError：稍后再试
        setTimeout(function () {
          if (!wantListen || myGen !== gen) return;
          try {
            if (rec) rec.start();
          } catch (e2) {
            onError(String(e2 && e2.message ? e2.message : e2));
            setStatus("无法启动麦克风");
            wantListen = false;
            setListeningUi(false);
          }
        }, 300);
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
        flushToFinal();
        return;
      }
      try {
        // 先 stop 拿最后结果；若无 onend，超时兜底 flush
        var r = rec;
        r.stop();
        setTimeout(function () {
          if (!flushed) {
            setListeningUi(false);
            flushToFinal();
            if (rec === r) {
              try {
                r.onend = null;
              } catch (_) {}
              rec = null;
            }
          }
        }, 600);
      } catch (_) {
        setListeningUi(false);
        flushToFinal();
        teardownRec(true);
      }
    }

    function toggle() {
      if (listening || wantListen) {
        stopListen();
      } else {
        wantListen = true;
        startListen(false);
      }
    }

    function setContinuousMulti(on) {
      multi = !!on;
      // multi 仅影响「结束后是否自动再开」；当前默认仍手动点结束
    }

    if (!isAvailable()) {
      btn.disabled = true;
      setStatus("本浏览器不支持语音（建议手机 Chrome）");
      onError("unsupported");
    } else {
      btn.addEventListener("click", function (ev) {
        if (ev && ev.cancelable) ev.preventDefault();
        toggle();
      });
      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
      });
      btn.textContent = "开始识别";
      setStatus("点「开始识别」说话，再说完点「结束识别」写入输入框");
    }

    return {
      kind: "voice",
      isAvailable: isAvailable,
      start: function () {
        wantListen = true;
        startListen(false);
      },
      stop: stopListen,
      toggle: toggle,
      isListening: function () {
        return listening;
      },
      setContinuousMulti: setContinuousMulti,
      // 兼容旧页
      setMode: function (m) {
        setContinuousMulti(m === "continuous");
      },
      getMode: function () {
        return multi ? "continuous" : "toggle";
      },
    };
  }

  global.AgentTaskVoiceInput = {
    mount: mount,
    isAvailable: isAvailable,
  };
})(typeof window !== "undefined" ? window : this);
