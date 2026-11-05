# 參數與進階使用

[回到使用說明](../README.md)

## 一般入口

從專案根目錄執行 `python -m epub3itizer --help` 查看完整參數，`--version` 查看版本。

| 參數 | 說明 |
| --- | --- |
| `input` | EPUB 檔或資料夾，必填 |
| `-o`、`--output` | 單檔輸出路徑 |
| `--output-dir` | 批次輸出資料夾 |
| `--recursive` | 遞迴搜尋子資料夾 |
| `--suffix` | 批次輸出檔名後綴；轉換預設 `_epub3`，修復預設 `_repaired` |
| `--overwrite` | 允許覆蓋已存在的批次輸出檔 |
| `--repair-only` | 只執行共用修復流程 |
| `--convert-chinese {none,s2tw}` | 文字轉換，預設 `none` |

未指定輸出時的實際命名應避免與來源混淆：資料夾模式預設使用來源名稱加模式後綴，例如 `books_epub3`；建議正式操作都明確指定輸出。

批次結束碼 `0` 表示這次處理沒有失敗項，`1` 表示有失敗項或執行錯誤。預設略過既有輸出，略過不代表重新驗證；`--overwrite` 才會覆蓋批次輸出。請閱讀逐本錯誤，不要只確認輸出資料夾存在就視為全部成功。

## 簡體轉臺灣正體

先將 [zhTranslate](https://github.com/SamLaio/zhTranslate) 安裝到同一 Python 環境：

```powershell
python -m pip install -e "D:\github\zhTranslate"
python -m epub3itizer ".\input.epub" -o ".\output.epub" --convert-chinese s2tw
python -m epub3itizer --repair-only ".\input.epub" -o ".\repaired.epub" --convert-chinese s2tw
```

上面的路徑是本機範例，可替換為實際 clone 位置。程式也支援本機 `D:\github\zhTranslate\src` 後備載入。只安裝 OpenCC 不等於已具備共用詞庫與轉換層。

只轉換 XHTML、OPF、NCX、XML 的可讀文字及允許的文字屬性（如 `title`、`alt`、`content`）；保留 `href`、`src`、`id`、CSS、URL、script/style。明確標示 `lang="ja"` 或 `xml:lang="ja"` 的日文區域保留，元素外中文尾文仍會轉換。引號與詞彙規則由 zhTranslate 維護。

已確認為正體的出版文字不要為了批次方便而重轉。輸出後仍需核對人名、專有名詞與歧義詞。

引號整理需搭配 zhTranslate 0.1.11 或更新版本。啟用 `--convert-chinese s2tw` 時，引號透過 zhTranslate 的獨立整理 API 處理，不要求節點含簡體字；純標點 `“？”`、`“……”` 與已正體中文對話也會轉換，而原有正體字詞不重轉。`pre`／`code`／`samp`／`kbd`、script/style、日文與 `translate="no"` 保留；屬性分隔符及 href/src/id 不改。半形直引號不跨行或跨 XML 節點猜配。

來源元素或其最近語言宣告明確為 `zh-Hans`、`zh-CN` 或 `zh-SG` 時，`s2tw` 會一併處理「此后」「一帘」等沒有其他明確簡體字的短句，並將該語言宣告改為 `zh-Hant`。未宣告簡體的文字維持保守偵測；巢狀正體語言、日文及 `translate="no"` 的保護仍生效。只有人工確認來源確為簡體時，才可在本機工作副本補上簡體語言宣告，不得用於已正體或來源不明的混合段落。

## Kindle 直排相容副本

此入口另需 `tinycss2`：

```powershell
python -m pip install tinycss2
python -m epub3itizer.kindle ".\original.epub" ".\kindle-vertical.epub" --keep-vertical --language zh-Hant
```

適用於已確認是中文直排、OPF spine 宣告 RTL 且需要嘗試 Send-to-Kindle 相容性的 EPUB3。`--keep-vertical` 只移除 spine 的 RTL 宣告，保留直排 CSS、固定頁、跨頁、SVG、viewport、圖片與正文。它改變宣告的閱讀方向，因此是選用操作，不會隨一般修復自動套用。

## Kindle 橫排流式副本

```powershell
python -m epub3itizer.kindle ".\original.epub" ".\kindle-horizontal.epub" --language zh-Hant
```

未加 `--keep-vertical` 時，入口將直排 CSS 改為橫排、spine 改為左至右，取消混合固定頁設定，並將可安全轉換的單圖 SVG 包裝改為可縮放插圖。只適合 EPUB3 文字書；全書固定版面、絕對定位或複雜 SVG 會停止，不能用來自動重排漫畫。

兩種 Kindle 模式都不接受輸入與輸出同檔。`--language` 只在確認內容語言後指定，同步 OPF 與 XHTML 根元素，不改局部外語標記。輸出後執行 EPUBCheck，再用 Previewer 或實際傳送檢查版面與字級調整。

KDP 與 Send-to-Kindle 是不同服務，規範檢查通過不能保證雲端接受。
