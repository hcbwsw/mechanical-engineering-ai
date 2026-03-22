# 界面截图（放这里）

把运行后的界面导出为 **PNG**（建议宽度 960～1280px），使用下表**固定文件名**保存到本目录，再 `git add` + `git push`。

| 文件名 | 内容 |
|--------|------|
| `unified-hub.png` | 浏览器打开 **Unified Application Hub** 后的整页 |
| `openapi-docs.png` | 浏览器打开 **`/docs`（Swagger）** 后的整页 |
| `dashboard.png` | **Mechanical Engineering AI Dashboard** 页面 |

## 在仓库首页 README 里展示

文件推送到 GitHub 后，在根目录 **`README.md`** 的「界面预览」一节中，使用**标准 Markdown**（兼容性最好）：

```markdown
### 界面预览

![统一入口 Hub](docs/screenshots/unified-hub.png)

![OpenAPI 文档](docs/screenshots/openapi-docs.png)

![诊断看板](docs/screenshots/dashboard.png)
```

可只保留已有截图对应的几行；**不要**在还没有真图时内嵌图片，否则容易出现裂图或误用占位块。

## 若 GitHub 仍不显示

1. 确认文件已出现在默认分支（多为 `main`）的 **`docs/screenshots/`** 下。  
2. 路径、**大小写**与 README 中完全一致。  
3. 使用 `![说明](docs/screenshots/xxx.png)`，避免复杂 HTML。  
4. 强制刷新浏览器（`Cmd+Shift+R`）。
