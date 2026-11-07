/**
 * 遥控 · 文字输入模块（独立）
 * 只负责 textarea 读写；不依赖语音模块。
 *
 * 用法：
 *   const text = AgentTaskTextInput.mount({ textareaId: "prompt" });
 *   text.getText(); text.setText("..."); text.clear(); text.append("...");
 */
(function (global) {
  "use strict";

  function mount(opts) {
    opts = opts || {};
    const id = opts.textareaId || "prompt";
    const el = document.getElementById(id);
    if (!el) {
      throw new Error("AgentTaskTextInput: missing #" + id);
    }

    function getText() {
      return String(el.value || "").trim();
    }

    function setText(s) {
      el.value = String(s == null ? "" : s);
      try {
        el.dispatchEvent(new Event("input", { bubbles: true }));
      } catch (_) {}
    }

    function clear() {
      setText("");
    }

    function append(s, sep) {
      const add = String(s == null ? "" : s).trim();
      if (!add) return getText();
      const cur = String(el.value || "").trim();
      const joiner = sep != null ? String(sep) : (cur ? "\n" : "");
      setText(cur ? cur + joiner + add : add);
      return getText();
    }

    function focus() {
      try {
        el.focus();
      } catch (_) {}
    }

    function rawElement() {
      return el;
    }

    return {
      kind: "text",
      getText: getText,
      setText: setText,
      clear: clear,
      append: append,
      focus: focus,
      rawElement: rawElement,
    };
  }

  function isAvailable() {
    return true;
  }

  global.AgentTaskTextInput = {
    mount: mount,
    isAvailable: isAvailable,
  };
})(typeof window !== "undefined" ? window : this);
