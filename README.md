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

### 單獨修復 EPUB

如果你已經有 EPUB3 檔，只想套用同一套修復規則，不需要重新做 EPUB2 -> EPUB3 轉換，可以用修復模式：

```bash
python -m epub3itizer --repair-only "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output_repaired.epub"
```

資料夾模式也支援批次修復：

```bash
python -m epub3itizer --repair-only "D:\project\epub223\testFile\books" --recursive --output-dir "D:\project\epub223\testFile\books_repaired"
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
- `--suffix`：批次輸出檔名後綴，轉換預設是 `_epub3`，修復預設是 `_repaired`
- `--overwrite`：覆蓋已存在的輸出檔
- `--repair-only`：只執行可重用的 EPUB 修復流程，不做 EPUB2 -> EPUB3 轉換

## 驗證

完成後可用 `epubCheck` 驗證：

```bash
java -jar "C:\PortableApps\[epub] epubCheck\epubcheck.jar" "D:\project\epub223\testFile\output.epub"
```

本專案目前已實測輸出可通過 `epubCheck`，顯示 `0 errors / 0 warnings`。

## 修復參考來源

當轉換結果無法通過 `epubCheck`，本專案會優先把可泛化的修復寫成
`epub3itizer` 內的 Python 規則，並補上回歸測試。以下工具只作為修復思路、
錯誤分類、驗證流程與測試案例設計的參考來源；不直接複製、移植或機械式改寫
第三方專案的程式碼。

- [calibre](https://github.com/kovidgoyal/calibre)：參考 Editor 的 Check book / auto-fix 思路。
- [Sigil](https://github.com/Sigil-Ebook/Sigil)：參考 Mend / Mend and Prettify / Mend On Open 思路。
- [rsking/epub-fixer](https://github.com/rsking/epub-fixer)
- [innocenat/kindle-epub-fix](https://github.com/innocenat/kindle-epub-fix)
- [amanvirparhar/gempress](https://github.com/amanvirparhar/gempress)
- [Mimoja/MyBookLibrary](https://github.com/Mimoja/MyBookLibrary)
- [dankatri/epub-fixer](https://github.com/dankatri/epub-fixer)
- [chodzkos/epubforge](https://github.com/chodzkos/epubforge)
- [crdjm/epub-accessibility-fixer](https://github.com/crdjm/epub-accessibility-fixer)
- [OpenBookPublishers/obp-epub-fixup](https://github.com/OpenBookPublishers/obp-epub-fixup)
- [madeindjs/epub-code-block-fixer](https://github.com/madeindjs/epub-code-block-fixer)：參考程式碼區塊、`pre` / `code` 與 XHTML 輸出清理。
- [veripublica/epubsana](https://github.com/veripublica/epubsana)：參考 EPUBCheck 類錯誤到安全修復 proposal 的分類方式。
- [RajaaKahel/epubfix](https://github.com/RajaaKahel/epubfix)：參考 Kobo / RMSDK 對現代 CSS 不相容時的 fallback 思路。
- [NRGunby/clean_epub](https://github.com/NRGunby/clean_epub)：參考掃描書常見頁首、頁碼與段落斷行污染清理。
- [cerasnix/epub-ruby-fix-for-apple-books](https://github.com/cerasnix/epub-ruby-fix-for-apple-books)：參考 ruby / rt / rp 在 Apple Books 顯示與選取相容性問題。
- [JoeCotellese/bookery](https://github.com/JoeCotellese/bookery)：參考 metadata-first 與非破壞式 EPUB metadata workflow。
- [chayprabs/epub-validate-repair](https://github.com/chayprabs/epub-validate-repair)：參考 manifest、spine、TOC、metadata 與批次驗證修復流程。

## 與 Sigil plugin 版的差異

除了 UI 之外，主要差異是：

- CLI 版直接讀取檔案系統，不需要先開 Sigil
- CLI 版輸出路徑由命令列參數控制
- CLI 版多了批次資料夾轉換
- plugin 版依賴 Sigil 的書籍狀態、選單與儲存流程
- 核心轉換邏輯仍然共用同一套程式碼

換句話說，這個 CLI 版是把原本 plugin 的核心轉換能力抽出來，讓它可以獨立跑，也比較適合大量 EPUB2 檔案的批次處理。

## 專案與授權

此專案由 [SamLaio](https://github.com/SamLaio) 維護。

程式源引自以下上游專案：

- [kevinhendricks/ePub3-itizer](https://github.com/kevinhendricks/ePub3-itizer)
- [Sigil-Ebook/Sigil](https://github.com/Sigil-Ebook/Sigil)

它改寫自早期的 Sigil `ePub3-itizer` 核心，但目前已經是獨立的 CLI 工具。

授權採 GNU General Public License v3.0，完整內容請見 [`COPYING.txt`](COPYING.txt)。
