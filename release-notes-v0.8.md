# ePub223 v0.8

## 變更

- 新增 OPF metadata/manifest XML id 衝突修復，避免 EPUBCheck 回報 `Duplicate "title"` 等錯誤。
- 簡轉正 `--convert-chinese s2tw` 改為優先使用 `D:\github\zhTranslate` 共用文字轉換層。
- CSS 清理新增移除 `text-combine: horizontal;`、`duokan-text-indent: 0;`，並修正常見方向屬性誤寫。
- CSS 與 inline style 清理會移除重複屬性宣告，保留最後一次宣告。
- nav/toc 修復強化：處理父層目錄順序倒退、普通清單 nav、空 `<dd/>` 目錄與單鏈巢狀 nav。
- XHTML 清理新增移除明確來源廣告與站台浮水印的規則。

## 驗證

- `python -m pytest -q`
