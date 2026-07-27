/* ============================================================
   全局脚本：导航高亮、Flash 自动关闭等
   ============================================================ */
(function () {
  "use strict";

  // 根据当前 URL 高亮对应的导航项
  function highlightNav() {
    const path = window.location.pathname;
    const links = document.querySelectorAll(".site-navbar .nav-link");
    links.forEach(function (link) {
      const href = link.getAttribute("href") || "";
      if (href === path) {
        link.classList.add("active");
      }
    });
  }

  // Flash 消息 5 秒后自动消失
  function autoDismissAlerts() {
    document.querySelectorAll(".alert").forEach(function (el) {
      setTimeout(function () {
        const alert = bootstrap.Alert.getOrCreateInstance(el);
        alert.close();
      }, 5000);
    });
  }

  /* ---------- 双击取消筛选 ----------
     已选中的标签 / 归档项带有 data-clear-url，
     单击 → 正常跳转（应用筛选），双击 → 跳到 data-clear-url（取消筛选）。
     用 250ms 延时区分单击与双击，避免单击抢先导航。
  */
  function setupFilterDblClickClear() {
    document.querySelectorAll("[data-clear-url]").forEach(function (el) {
      var timer = null;
      el.addEventListener("click", function (e) {
        if (timer) {
          // 第二次点击在 250ms 内到达 → 双击：取消筛选
          clearTimeout(timer);
          timer = null;
          e.preventDefault();
          window.location.href = el.dataset.clearUrl;
          return;
        }
        // 第一次点击：延时等待，看是否有第二次点击
        e.preventDefault();
        timer = setTimeout(function () {
          timer = null;
          window.location.href = el.href;
        }, 250);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    highlightNav();
    autoDismissAlerts();
    setupFilterDblClickClear();
  });
})();
