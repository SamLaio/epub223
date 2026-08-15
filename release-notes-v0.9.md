# ePub223 v0.9

## 這版更新

- 強化 `repair-only` 對空檔、不可解析 XHTML、缺少 nav、缺少 `dcterms:modified` 與私有 OPF metadata 的修復。
- 新增多項 EPUBCheck 導向修復：XHTML entity、圖片 spine、nav 指向圖片或非 spine、metadata id 衝突、固定版面 viewport、失效 `@import`、不合法 OPF 欄位等。
- CSS sanitizer 新增移除 `text-spacing-trim: trim-start;`，並持續清理閱讀器私有或 EPUBCheck 不友善宣告。

## 驗證

- `python -m pytest -q`
