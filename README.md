# epub223

將 EPUB2 轉成 EPUB3，或修復既有 EPUB 的命令列工具。支援單本、資料夾與遞迴批次，整理 OPF、XHTML、導覽目錄及資源引用，輸出獨立的工作檔。

適合已有 EPUB、需要轉換格式或修正結構的使用者。TXT 建書請用 ezPub；CSS 專項檢查可接續使用 epubCssFixer。

目前版本：**1.11**。版本異動見 [CHANGELOG](CHANGELOG.md)。

## 安裝與快速開始

在專案根目錄準備 Python 與 `lxml`：

```powershell
python -m pip install lxml
python -m epub3itizer ".\input.epub" -o ".\output.epub"
```

不需要開啟 Sigil。`python convert_epub3.py` 是相容舊入口；以下統一使用模組入口。

已有 EPUB3，只想修復結構：

```powershell
python -m epub3itizer --repair-only ".\input.epub" -o ".\repaired.epub"
```

請讓輸入與輸出使用不同路徑。保留原檔，在驗證輸出後再決定是否替換。

## 選擇處理模式

| 需求 | 指令／選項 |
| --- | --- |
| EPUB2 → EPUB3 | `python -m epub3itizer input.epub -o output.epub` |
| 只套用結構修復 | 加上 `--repair-only` |
| 簡體轉臺灣正體 | 明確加上 `--convert-chinese s2tw` |
| 整個資料夾 | 輸入改為資料夾，使用 `--output-dir` |
| 包含子資料夾 | 加上 `--recursive` |
| Kindle 相容副本 | 使用獨立入口，見 [進階使用](docs/usage.md) |

一般轉換不會自動簡轉正，也不會自動套用 Kindle 專用版面轉換。

## 資料夾批次

```powershell
python -m epub3itizer ".\books" --recursive --output-dir ".\books_epub3"
python -m epub3itizer --repair-only ".\books" --recursive --output-dir ".\books_repaired"
```

保留來源的子資料夾結構。單檔輸出用 `-o`，批次輸出用 `--output-dir`。預設輸出命名、覆蓋選項與結束碼見 [進階使用](docs/usage.md)。

## 驗證輸出

工具成功輸出不等於 EPUB 規範或閱讀器驗收通過。建議依序檢查 CSS、執行外部 EPUBCheck，再回讀目錄、註腳、圖片及正文。

修復保留包內嵌入字型的 `@font-face` 與內文／標題的字型連結；最終驗證仍須確認 CSS 指向實際存在的字型資源，詳見[修復範圍](docs/repair.md)。

```powershell
java -jar "C:\path\to\epubcheck.jar" ".\output.epub"
```

EPUBCheck 與可執行它的 Java 環境只用於外部驗證，不是轉換必要依賴；Java 版本請依所用 EPUBCheck 版本準備。Send-to-Kindle 是否接受仍需實際傳送確認。

## 詳細說明

- [參數、簡轉正與 Kindle 模式](docs/usage.md)
- [修復範圍、安全界線與參考來源](docs/repair.md)
- [版本紀錄](CHANGELOG.md)

## 開發與授權

CLI 位於 `epub3itizer/cli.py`，主要轉換在 `epub3itizer/conversion.py`，測試在 `tests/`。測試指令：`python -m pytest -q`。

此專案源自 [kevinhendricks/ePub3-itizer](https://github.com/kevinhendricks/ePub3-itizer) 與 [Sigil](https://github.com/Sigil-Ebook/Sigil) 的轉換核心，現為獨立 CLI，由 [SamLaio](https://github.com/SamLaio) 維護。授權 GNU GPL v3，見 [LICENSE](LICENSE)。

## 第三方來源與致謝

### 上游程式碼與作者

- [Kevin B. Hendricks／ePub3-itizer](https://github.com/kevinhendricks/ePub3-itizer)：本專案沿用並調整的 EPUB2→3 轉換核心；`src/plugin.py` 保留 Copyright 2015–2020 Kevin B. Hendricks 與 LGPL 2.1／LGPL 3 授權聲明。`src/opf_converter.py`、`src/html_namedentities.py` 與 plugin 設定亦保留於來源目錄；個別檔案以其原始聲明及上游內容為準。
- [Sigil／Sigil-Ebook 團隊](https://github.com/Sigil-Ebook/Sigil)：原 plugin 執行環境及相關開發脈絡；CLI 不需要啟動 Sigil。
- [Alberto Pettarin](https://www.albertopettarin.it/)：上游 ePub3-itizer 明列的 Media Overlay metadata 處理貢獻者；保留這項上游致謝，不將相關處理概括為本專案原創。
- Doug Massay：`src/plugin_utils_light.py` 保留 Copyright (c) 2025 Doug Massay、BSD-2-Clause 條款與免責聲明；此檔為保留的 plugin 輔助程式，非一般 CLI 的必要介面。

本專案根目錄 `LICENSE` 為 GPL v3；這不會移除上述上游檔案原有的署名、授權條件或免責聲明。

### 實際使用與外部工具

| 專案 | 使用範圍 | 上游授權 |
| --- | --- | --- |
| [lxml](https://github.com/lxml/lxml) | EPUB XML／HTML 解析 | BSD-3-Clause；底層元件另依各自授權 |
| [tinycss2／CourtBouillon](https://github.com/Kozea/tinycss2) | 選用 Kindle 模式的 CSS 解析 | BSD-3-Clause |
| [zhTranslate](https://github.com/SamLaio/zhTranslate) | 選用簡轉正的共用文字層 | GPL-3.0-or-later |
| [OpenCC](https://github.com/BYVoid/OpenCC)／[Python 實作](https://github.com/yichen0831/opencc-python) | 經 zhTranslate 使用轉換設定與字典 | Apache-2.0 |
| [EPUBCheck／W3C](https://github.com/w3c/epubcheck) | 外部格式驗證，不是轉換執行依賴 | BSD-3-Clause |

### 修復思路與規範參考

下列項目是既有文件記錄的修復思路、錯誤分類或測試設計參考；列出參考不表示複製其程式碼、整合全部功能或以其授權重新授權本專案。具體範圍見 [修復手冊](docs/repair.md)。

- [calibre](https://github.com/kovidgoyal/calibre)：參考 Editor 的 Check book / auto-fix 思路。
- [Sigil](https://github.com/Sigil-Ebook/Sigil)：參考 Mend / Mend and Prettify / Mend On Open 思路。
- [rsking/epub-fixer](https://github.com/rsking/epub-fixer)
- [innocenat/kindle-epub-fix](https://github.com/innocenat/kindle-epub-fix)：參考 UTF-8 宣告與 body ID 目錄連結修復。
- [imanubdesigner/epub-kindle-fix](https://github.com/imanubdesigner/epub-kindle-fix)：另參考資源、MIME、XML 與連結檢查。
- [dliedke/Kindle-EPUB-Fix](https://github.com/dliedke/Kindle-EPUB-Fix)：參考本機瀏覽器診斷、結構與資源檢查及 JSON 報告設計；列為參考，不代表已整合其全部修復。
- [w3c/epubcheck](https://github.com/w3c/epubcheck)：作為轉換後的外部 EPUB 規範驗證工具；不是轉換必要依賴，也不能單獨判定 Kindle 轉換一定成功。
- [amanvirparhar/gempress](https://github.com/amanvirparhar/gempress)
- [Mimoja/MyBookLibrary](https://github.com/Mimoja/MyBookLibrary)
- [dankatri/epub-fixer](https://github.com/dankatri/epub-fixer)
- [chodzkos/epubforge](https://github.com/chodzkos/epubforge)
- [crdjm/epub-accessibility-fixer](https://github.com/crdjm/epub-accessibility-fixer)
- [OpenBookPublishers/obp-epub-fixup](https://github.com/OpenBookPublishers/obp-epub-fixup)
- [Hopkins1/TradSimpChinese](https://github.com/Hopkins1/TradSimpChinese)：參考簡繁轉換中的引號格式轉換方式。
- [madeindjs/epub-code-block-fixer](https://github.com/madeindjs/epub-code-block-fixer)：參考程式碼區塊、`pre` / `code` 與 XHTML 輸出清理。
- [veripublica/epubsana](https://github.com/veripublica/epubsana)：參考 EPUBCheck 類錯誤到安全修復 proposal 的分類方式。
- [RajaaKahel/epubfix](https://github.com/RajaaKahel/epubfix)：參考 Kobo / RMSDK 對現代 CSS 不相容時的 fallback 思路。
- [NRGunby/clean_epub](https://github.com/NRGunby/clean_epub)：參考掃描書常見頁首、頁碼與段落斷行污染清理。
- [cerasnix/epub-ruby-fix-for-apple-books](https://github.com/cerasnix/epub-ruby-fix-for-apple-books)：參考 ruby / rt / rp 在 Apple Books 顯示與選取相容性問題。
- [JoeCotellese/bookery](https://github.com/JoeCotellese/bookery)：參考 metadata-first 與非破壞式 EPUB metadata workflow。
- [chayprabs/epub-validate-repair](https://github.com/chayprabs/epub-validate-repair)：參考 manifest、spine、TOC、metadata 與批次驗證修復流程。
