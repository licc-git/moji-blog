/* ============================================================
   编辑器脚本：实时预览 + 文件上传 + AI 助手
   依赖：浏览器原生 fetch，无需第三方库
   URL 等配置通过 window.MO_EDITOR_CONFIG 注入（见 edit.html）
   ============================================================ */
(function () {
  "use strict";

  const cfg = window.MO_EDITOR_CONFIG || {};
  const previewUrl = cfg.previewUrl || "";
  const uploadUrl = cfg.uploadUrl || "";
  const aiActionsUrl = cfg.aiActionsUrl || "";
  const aiAssistUrl = cfg.aiAssistUrl || "";
  const newCategoryUrl = cfg.newCategoryUrl || "";

  const textarea = document.getElementById("editor-textarea");
  const preview = document.getElementById("editor-preview");
  const charCount = document.getElementById("char-count");
  const form = document.getElementById("post-form");
  if (!textarea || !preview) return;

  const csrfInput = document.querySelector("input[name=csrf_token]");
  const csrfToken = csrfInput ? csrfInput.value : "";
  const jsonHeaders = {
    "X-CSRFToken": csrfToken,
    "Content-Type": "application/json",
  };
  const formHeaders = { "X-CSRFToken": csrfToken };

  let previewTimer = null;
  let lastResult = ""; // AI 最近一次返回的结果

  /* ---------- 实时预览（防抖） ---------- */
  function schedulePreview() {
    updateCharCount();
    clearTimeout(previewTimer);
    previewTimer = setTimeout(renderPreview, 350);
  }

  function updateCharCount() {
    charCount.textContent = textarea.value.length + " 字";
  }

  function renderPreview() {
    const text = textarea.value;
    if (!text.trim()) {
      preview.innerHTML =
        '<p class="text-muted small">在左侧输入 Markdown，这里会实时显示渲染效果。</p>';
      return;
    }
    fetch(previewUrl, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ text: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        preview.innerHTML = data.html || "";
        if (window.hljs) {
          preview.querySelectorAll("pre code").forEach(function (el) {
            hljs.highlightElement(el);
          });
        }
        // 公式渲染：让 MathJax 对新插入的内容重新排版
        if (window.MathJax && window.MathJax.typesetPromise) {
          window.MathJax.typesetPromise([preview]).catch(function () {});
        }
      })
      .catch(function () {
        preview.innerHTML = '<p class="text-danger small">预览失败，请检查网络。</p>';
      });
  }

  textarea.addEventListener("input", schedulePreview);
  // 初始化预览
  schedulePreview();

  /* ---------- 文件上传 ---------- */
  const hiddenInput = document.getElementById("hidden-file-input");
  const btnImg = document.getElementById("btn-upload-img");
  const btnFile = document.getElementById("btn-upload-file");

  function triggerUpload(mode) {
    hiddenInput.value = "";
    // 图片模式仅允许图片
    hiddenInput.accept = mode === "img" ? "image/*" : "";
    hiddenInput.click();
  }

  if (btnImg) btnImg.addEventListener("click", function () { triggerUpload("img"); });
  if (btnFile) btnFile.addEventListener("click", function () { triggerUpload("file"); });

  hiddenInput.addEventListener("change", function () {
    if (hiddenInput.files && hiddenInput.files[0]) {
      uploadFile(hiddenInput.files[0]);
    }
  });

  function uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("csrf_token", csrfToken);

    const toast = showToast("正在上传 " + file.name + "…");

    fetch(uploadUrl, {
      method: "POST",
      headers: formHeaders,
      body: fd,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        toast.remove();
        if (data.ok) {
          insertAtCursor(data.markdown);
          renderPreview();
          showToast("已插入：" + data.file.name, "success");
        } else {
          showToast("上传失败：" + (data.error || "未知错误"), "danger");
        }
      })
      .catch(function () {
        toast.remove();
        showToast("上传失败：网络错误", "danger");
      });
  }

  /* ---------- 拖拽上传 ---------- */
  const dropOverlay = document.createElement("div");
  dropOverlay.className = "drop-overlay";
  dropOverlay.innerHTML = "松手即可上传";
  document.body.appendChild(dropOverlay);

  let dragCounter = 0;
  textarea.addEventListener("dragenter", function (e) {
    e.preventDefault();
    dragCounter++;
    dropOverlay.classList.add("show");
  });
  textarea.addEventListener("dragover", function (e) { e.preventDefault(); });
  textarea.addEventListener("dragleave", function () {
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      dropOverlay.classList.remove("show");
    }
  });
  textarea.addEventListener("drop", function (e) {
    e.preventDefault();
    dragCounter = 0;
    dropOverlay.classList.remove("show");
    if (e.dataTransfer && e.dataTransfer.files.length) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  /* ---------- 在光标处插入文本 ---------- */
  function insertAtCursor(text) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = textarea.value.substring(0, start);
    const after = textarea.value.substring(end);
    const insertText = (before && !before.endsWith("\n") ? "\n" : "") + text + "\n";
    textarea.value = before + insertText + after;
    const pos = start + insertText.length;
    textarea.selectionStart = textarea.selectionEnd = pos;
    textarea.focus();
    schedulePreview();
  }

  /* ---------- 行内插入（不加换行，用于符号 / 行内代码 / 公式等） ---------- */
  function insertInline(text) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = textarea.value.substring(0, start);
    const after = textarea.value.substring(end);
    textarea.value = before + text + after;
    const pos = start + text.length;
    textarea.selectionStart = textarea.selectionEnd = pos;
    textarea.focus();
    schedulePreview();
  }

  /* ---------- 快捷插入：工具条 [data-insert] 按钮 ---------- */
  // 模板表：key → Markdown 文本
  const MD_TEMPLATES = {
    inline_code: "`code`",
    code_block: "\n```python\n\n```\n",
    inline_math: "$x$",
    block_math: "\n$$\n\n$$\n",
    h2: "## ",
    quote: "> ",
    link: "[文本](url)",
    table: "\n| 列1 | 列2 | 列3 |\n| --- | --- | --- |\n| | | |\n",
    hr: "\n---\n",
  };
  // 块级模板：用 insertAtCursor（前后补换行）；其余行内用 insertInline
  const BLOCK_INSERTS = { code_block: 1, block_math: 1, table: 1, hr: 1 };

  document.querySelectorAll("[data-insert]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const key = btn.getAttribute("data-insert");
      const tpl = MD_TEMPLATES[key];
      if (!tpl) return;
      if (BLOCK_INSERTS[key]) insertAtCursor(tpl);
      else insertInline(tpl);
    });
  });

  /* ---------- 符号面板：toggle 显示 + 点击插入符号 ---------- */
  const symbolPalette = document.getElementById("symbol-palette");
  const btnSymbols = document.getElementById("btn-symbols");
  if (btnSymbols && symbolPalette) {
    btnSymbols.addEventListener("click", function () {
      symbolPalette.hidden = !symbolPalette.hidden;
    });
    symbolPalette.addEventListener("click", function (e) {
      const target = e.target.closest("[data-symbol]");
      if (!target) return;
      insertInline(target.getAttribute("data-symbol"));
    });
  }

  /* ---------- 新建分类（编辑页内联 AJAX） ---------- */
  const btnNewCat = document.getElementById("btn-new-category");
  const btnSaveCat = document.getElementById("btn-save-category");
  const catSelect = document.getElementById("category_id");
  const catNameInput = document.getElementById("new-cat-name");
  const catDescInput = document.getElementById("new-cat-desc");
  const catErrBox = document.getElementById("new-cat-error");

  function openNewCatModal() {
    const modalEl = document.getElementById("newCatModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    catErrBox.style.display = "none";
    catNameInput.value = "";
    catDescInput.value = "";
    modal.show();
    setTimeout(function () { catNameInput.focus(); }, 200);
  }

  if (btnNewCat) btnNewCat.addEventListener("click", openNewCatModal);

  if (btnSaveCat) {
    btnSaveCat.addEventListener("click", function () {
      const name = catNameInput.value.trim();
      const desc = catDescInput.value.trim();
      catErrBox.style.display = "none";
      if (!name) {
        catErrBox.textContent = "分类名不能为空";
        catErrBox.style.display = "block";
        return;
      }
      btnSaveCat.disabled = true;
      fetch(newCategoryUrl, {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ name: name, description: desc }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          btnSaveCat.disabled = false;
          if (data.ok) {
            // 追加到分类下拉并自动选中
            const opt = document.createElement("option");
            opt.value = data.category.id;
            opt.textContent = data.category.name;
            catSelect.appendChild(opt);
            catSelect.value = data.category.id;
            bootstrap.Modal.getOrCreateInstance(
              document.getElementById("newCatModal")
            ).hide();
            showToast("已新建分类：" + data.category.name, "success");
          } else {
            catErrBox.textContent = data.error || "创建失败";
            catErrBox.style.display = "block";
          }
        })
        .catch(function () {
          btnSaveCat.disabled = false;
          catErrBox.textContent = "网络错误，请稍后再试";
          catErrBox.style.display = "block";
        });
    });
  }

  /* ---------- AI 助手 ---------- */
  const aiPanel = document.getElementById("ai-panel");
  const aiResult = document.getElementById("ai-result");
  const aiAfter = document.getElementById("ai-actions-after");
  const btnToggleAi = document.getElementById("btn-toggle-ai");
  const aiProviderTag = document.getElementById("ai-provider-tag");

  if (btnToggleAi) {
    btnToggleAi.addEventListener("click", function () {
      const shown = aiPanel.style.display !== "none";
      aiPanel.style.display = shown ? "none" : "block";
      if (!shown) loadAiActions();
    });
  }

  function loadAiActions() {
    fetch(aiActionsUrl, { headers: formHeaders })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          aiProviderTag.textContent = "服务：" + data.provider;
        }
      })
      .catch(function () {});
  }

  document.querySelectorAll("[data-action]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const action = btn.getAttribute("data-action");
      const text = textarea.value.trim();
      if (!text && action !== "continue") {
        showToast("正文为空，无法执行 AI 操作。", "warning");
        return;
      }
      runAi(action, text);
    });
  });

  function runAi(action, text) {
    aiResult.classList.add("show");
    aiResult.innerHTML = '<span class="ai-loading"></span> AI 思考中…';
    aiAfter.style.display = "none";

    fetch(aiAssistUrl, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ action: action, text: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          lastResult = data.result;
          aiResult.textContent = data.result;
          aiAfter.style.display = "flex";
        } else {
          aiResult.innerHTML =
            '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> ' +
            (data.error || "调用失败") + "</span>";
        }
      })
      .catch(function () {
        aiResult.innerHTML =
          '<span class="text-danger">网络错误，请稍后再试。</span>';
      });
  }

  // 采纳 / 追加 / 填摘要
  const applyBtn = document.getElementById("ai-apply");
  const appendBtn = document.getElementById("ai-append");
  const summaryBtn = document.getElementById("ai-summary-fill");
  if (applyBtn) applyBtn.addEventListener("click", function () {
    if (lastResult) {
      textarea.value = lastResult;
      schedulePreview();
      showToast("已用 AI 结果替换正文。", "success");
    }
  });
  if (appendBtn) appendBtn.addEventListener("click", function () {
    if (lastResult) {
      insertAtCursor(lastResult);
      showToast("已追加到正文末尾。", "success");
    }
  });
  if (summaryBtn) summaryBtn.addEventListener("click", function () {
    if (lastResult) {
      const summaryInput = document.getElementById("summary");
      if (summaryInput) {
        summaryInput.value = lastResult.replace(/\n+/g, " ").trim().slice(0, 500);
        showToast("已填入摘要。", "success");
      }
    }
  });

  /* ---------- Toast 提示 ---------- */
  function showToast(msg, type) {
    type = type || "info";
    const colors = {
      info: "bg-dark", success: "bg-success",
      danger: "bg-danger", warning: "bg-warning text-dark",
    };
    const el = document.createElement("div");
    el.className =
      "position-fixed top-0 start-50 translate-middle-x mt-3 px-3 py-2 " +
      "rounded shadow text-white " + (colors[type] || colors.info);
    el.style.zIndex = 2000;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () {
      el.style.transition = "opacity .3s";
      el.style.opacity = 0;
      setTimeout(function () { el.remove(); }, 300);
    }, 2600);
    return el;
  }

  /* ---------- 保存：AJAX 无跳转 + Ctrl+S + 5 秒自动保存 ---------- */
  const saveStatus = document.getElementById("save-status");
  let dirty = false;
  let saving = false;
  const original = textarea.value;

  /* 客户端基本校验：标题和正文不能为空（避免无效自动保存） */
  function canSave() {
    const titleInput = document.getElementById("title");
    return titleInput && titleInput.value.trim() && textarea.value.trim();
  }

  /* AJAX 保存：POST 表单数据，服务端返回 JSON，页面不跳转 */
  function saveDraft(silent) {
    if (saving) return;                 // 防止重复提交
    if (!canSave()) {
      if (!silent) showToast("标题和正文不能为空", "warning");
      return;
    }
    saving = true;
    if (saveStatus) {
      saveStatus.textContent = "保存中…";
      saveStatus.className = "save-status saving";
    }

    const formData = new FormData(form);
    fetch(form.action || window.location.pathname, {
      method: "POST",
      headers: { "Accept": "application/json", "X-CSRFToken": csrfToken },
      body: formData,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        saving = false;
        if (data.ok) {
          dirty = false;
          if (saveStatus) {
            saveStatus.textContent = "已保存 ✓";
            saveStatus.className = "save-status saved";
            setTimeout(function () {
              saveStatus.textContent = "";
              saveStatus.className = "save-status";
            }, 2000);
          }
          /* 新建文章首次保存后：把表单 action 切到编辑路由，后续保存走 edit */
          if (data.is_new && data.redirect_url) {
            form.setAttribute("action", data.redirect_url);
            window.history.replaceState(null, "", data.redirect_url);
          }
          if (!silent) showToast("已保存", "success");
        } else {
          if (saveStatus) {
            saveStatus.textContent = "保存失败";
            saveStatus.className = "save-status error";
          }
          if (!silent) showToast("保存失败", "danger");
        }
      })
      .catch(function () {
        saving = false;
        if (saveStatus) {
          saveStatus.textContent = "网络错误";
          saveStatus.className = "save-status error";
        }
        if (!silent) showToast("保存失败：网络错误", "danger");
      });
  }

  /* Ctrl+S / Cmd+S → 保存（拦截浏览器默认的「另存为」） */
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      saveDraft(false);
    }
  });

  /* Tab 键缩进：在编辑器内按 Tab 插入 2 空格（非切换焦点），符合 Markdown 习惯。
     - 无选区：光标处插入 2 空格
     - 有选区：选中每行行首加 2 空格（批量缩进）
     - Shift+Tab：选中每行行首去掉 2 空格（反缩进） */
  textarea.addEventListener("keydown", function (e) {
    if (e.key !== "Tab") return;
    e.preventDefault();
    var start = this.selectionStart;
    var end = this.selectionEnd;
    var value = this.value;

    if (e.shiftKey) {
      // 反缩进：选中区涉及的每行去掉行首 1~2 个空格
      var lineStart = value.lastIndexOf("\n", start - 1) + 1;
      var segment = value.slice(lineStart, end);
      var replaced = segment.replace(/^ {1,2}/gm, "");
      this.value = value.slice(0, lineStart) + replaced + value.slice(end);
      this.selectionStart = lineStart;
      this.selectionEnd = lineStart + replaced.length;
    } else if (start !== end) {
      // 有选区：每行行首加 2 空格
      var lineStart = value.lastIndexOf("\n", start - 1) + 1;
      var segment = value.slice(lineStart, end);
      var replaced = segment.replace(/^/gm, "  ");
      this.value = value.slice(0, lineStart) + replaced + value.slice(end);
      this.selectionStart = lineStart;
      this.selectionEnd = lineStart + replaced.length;
    } else {
      // 无选区：光标处插入 2 空格
      this.value = value.slice(0, start) + "  " + value.slice(end);
      this.selectionStart = this.selectionEnd = start + 2;
    }
    dirty = true;
    schedulePreview();
  });

  /* 保存按钮提交 → AJAX 保存（不跳转页面） */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    saveDraft(false);
  });

  /* 标记脏数据：任何表单字段改动都标记 */
  form.querySelectorAll("input, textarea, select").forEach(function (el) {
    if (el === textarea) return;       // textarea 已在下方绑定 input
    el.addEventListener("input", function () { dirty = true; });
    el.addEventListener("change", function () { dirty = true; });
  });

  /* 自动保存：每 5 秒检查，有改动且非保存中才保存（静默，不弹 toast） */
  setInterval(function () {
    if (dirty && !saving && canSave()) {
      saveDraft(true);
    }
  }, 5000);

  /* 离开前提醒（有未保存改动时） */
  window.addEventListener("beforeunload", function (e) {
    if (dirty && textarea.value !== original) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
})();
