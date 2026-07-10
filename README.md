# ePub223

這是把原本的 Sigil `ePub3-itizer` plugin 核心整理成獨立 CLI 專案的版本。

用途很單純：

- 把 EPUB2 轉成 EPUB3
- 支援單一 EPUB 檔轉換
- 支援整個資料夾批次轉換
- 不依賴 Sigil 介面

## 功能

- 保留原本的 EPUB2 -> EPUB3 轉換邏輯
- 直接從命令列處理單檔
- 資料夾批次轉換
- 可遞迴掃描子資料夾
- 轉換時保留原始資料夾結構
- 可搭配 `epubCheck` 驗證輸出檔

## 專案結構

```text
convert_epub3.py        # 舊入口相容包裝
epub3itizer/            # CLI 主程式
  __main__.py
  cli.py
  compat.py
  conversion.py
plugin/                 # 原始 Sigil plugin 相關檔案
src/                    # 原始轉換輔助模組
tests/                  # 測試資料
```

## 需求

- Python
- `lxml`

如果你是直接從原始碼執行，轉換功能本身通常只需要先安裝 `lxml`。

```bash
pip install lxml
```

如果你想在轉換後額外跑 `epubCheck` 驗證，才需要 Java 8+ 或可執行 `java -jar` 的環境。

## 使用方式

### 單一檔案轉換

```bash
python convert_epub3.py "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output.epub"
```

也可以直接用模組入口：

```bash
python -m epub3itizer "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output.epub"
```

### 整個資料夾批次轉換

```bash
python -m epub3itizer "D:\project\epub223\epub2" --recursive --output-dir "D:\project\epub223\epub3"
```

如果你不指定 `--output-dir`，預設會輸出到：

```text
原資料夾名稱_epub3
```

例如：

```text
D:\project\epub223\epub2  ->  D:\project\epub223\epub2_epub3
```

### 常用參數

- `-o, --output`：單檔輸出路徑
- `--output-dir`：批次模式輸出資料夾
- `--recursive`：遞迴掃描子資料夾
- `--suffix`：批次輸出檔名後綴，預設是 `_epub3`
- `--overwrite`：覆蓋已存在的輸出檔

## 驗證

完成後可用 `epubCheck` 驗證：

```bash
java -jar "C:\PortableApps\[epub] epubCheck\epubcheck.jar" "D:\project\epub223\testFile\output.epub"
```

本專案目前已實測輸出可通過 `epubCheck`，顯示 `0 errors / 0 warnings`。

## 與 Sigil plugin 版的差異

除了 UI 之外，主要差異是：

- CLI 版直接讀取檔案系統，不需要先開 Sigil
- CLI 版輸出路徑由命令列參數控制
- CLI 版多了批次資料夾轉換
- plugin 版依賴 Sigil 的書籍狀態、選單與儲存流程
- 核心轉換邏輯仍然共用同一套程式碼

換句話說，這個 CLI 版是把原本 plugin 的核心轉換能力抽出來，讓它可以獨立跑，也比較適合大量 EPUB2 檔案的批次處理。

## 專案與授權

此專案由 [SamLaio](https://github.com/SamLaio) 維護，屬於我的專案。

它改寫自早期的 Sigil `ePub3-itizer` 核心，但目前已經是獨立的 CLI 工具。

授權採 GNU General Public License v3.0，完整內容請見 [`COPYING.txt`](COPYING.txt)。
