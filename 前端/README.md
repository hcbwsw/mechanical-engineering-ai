# 前端（静态演示页）

- **入口**：`Unified Application Hub.html` — 点击卡片在 iframe 中打开各模块页面。
- **同目录 HTML**：文件名带空格是历史命名；Hub 内 `MODULE_HTML` 已指向这些真实文件名。
- **推荐访问方式**：在本目录执行 `python3 -m http.server 8080`，用浏览器打开  
  `http://127.0.0.1:8080/Unified%20Application%20Hub.html`  
  （避免部分浏览器对 `file://` 下 iframe 加载本地页的限制。）

API 基地址一般在各页内写死为 `localhost:8000` 等，若对接 **main_app**（默认 **8010**），需在对应 HTML 的脚本里改 `baseUrl` / `API_URL`。
