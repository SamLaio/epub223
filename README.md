# epub223

將 EPUB2 轉成 EPUB3，或修復既有 EPUB 的命令列工具。支援單本、資料夾與遞迴批次，整理 OPF、XHTML、導覽目錄及資源引用，輸出獨立的工作檔。

適合已有 EPUB、需要轉換格式或修正結構的使用者。TXT 建書請用 ezPub；CSS 專項檢查可接續使用 epubCssFixer。

目前版本：**1.9**。版本異動見 [CHANGELOG](CHANGELOG.md)。

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
