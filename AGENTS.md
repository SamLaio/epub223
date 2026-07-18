# ePub223 Agent Rules

本檔是 `ePub223` 專案的 agent / Codex 慣例檔。修改程式、文件、測試或發版前，先依照這裡的規則檢查。

## 專案定位

- 這個專案的核心目標是把 EPUB2 轉成 EPUB3。
- 目前不做 UI，也不依賴 Sigil 介面。
- 轉換流程本身不應依賴 `epubCheck`。
- `epubCheck` 只用作轉換後的外部驗證，不是執行轉換的必要條件。

## 核心功能

目前專案重點如下：

- 單一 EPUB 檔轉換。
- 整個資料夾批次轉換。
- 可選遞迴掃描子資料夾。
- 可自訂輸出資料夾、檔名後綴與覆蓋行為。
- 保留原始資料夾結構。
- 盡量維持輸出 EPUB3 可通過 `epubCheck`。

## 主要檔案

- `convert_epub3.py`：舊入口相容包裝。
- `epub3itizer/cli.py`：CLI 入口與參數處理。
- `epub3itizer/conversion.py`：EPUB2 -> EPUB3 核心轉換。
- `epub3itizer/compat.py`：與原始 Sigil / EPUB 結構相容的輔助邏輯。
- `tests/`：回歸測試與範例素材。

## 文件一致性

- `README.md` 要和實際 CLI 行為一致。
- 如果功能變動，先更新 `README.md`，再考慮其他文件。
- `epubCheck` 相關內容要明確寫成「外部驗證」，不要寫成轉換的必要依賴。

## 驗證方式

- 修改轉換邏輯後，優先跑 `pytest -q`。
- 若變更可能影響輸出結構、OPF、nav、spine 或其他 EPUB 規則，除了測試外，必要時再手動跑 `epubCheck`。
- 如果只改 README 或說明文字，通常不需要額外跑 `epubCheck`，但仍要確認文字沒有誤導依賴關係。

## 修復規則來源

- 當 EPUBCheck 失敗需要新增自動修復規則時，優先檢查下列參考來源是否
  已有類似修復邏輯：
  - calibre Editor 的「Check book」/ auto-fix。
  - Sigil 的 Mend / Mend and Prettify / Mend On Open。
  - `rsking/epub-fixer`：https://github.com/rsking/epub-fixer
  - `innocenat/kindle-epub-fix`：https://github.com/innocenat/kindle-epub-fix
  - `amanvirparhar/gempress`：https://github.com/amanvirparhar/gempress
  - `Mimoja/MyBookLibrary`：https://github.com/Mimoja/MyBookLibrary
  - `dankatri/epub-fixer`：https://github.com/dankatri/epub-fixer
  - `chodzkos/epubforge`：https://github.com/chodzkos/epubforge
  - `crdjm/epub-accessibility-fixer`：https://github.com/crdjm/epub-accessibility-fixer
  - `OpenBookPublishers/obp-epub-fixup`：https://github.com/OpenBookPublishers/obp-epub-fixup
- 第三方修復專案只作為修復思路、錯誤分類、驗證流程與回歸測試設計的
  參考來源；不要直接複製、移植或機械式改寫其程式碼進本專案，除非使用者
  另行明確要求制定授權相容的實作方案。
- 若使用者提供 GitHub 專案連結並要求 Codex 參考，除了檢查其實作思路外，
  也要把該參考來源補進 `README.md` 的修復參考來源或相關功能說明中。
- 若參考來源有可泛化且適合批次處理的做法，將其思路改寫成
  `epub3itizer` 內可測的 Python 規則，並新增或更新回歸測試與
  `CHANGELOG.md`。
- `kindle-epub-fix` 主要作為 UTF-8 編碼宣告與 Send-to-Kindle 類問題的
  參考，不要將其過度泛化到無關的 EPUBCheck 結構錯誤。
- 只有在參考來源沒有相近邏輯、或該邏輯不適合無人值守批次轉換時，才
  由 Codex 另行判斷並設計修復方式。
- 任何需要 Codex 介入的 EPUB 修復，先分類為：
  - 可泛用修復規則。
  - 單本書特有破損。
  - 不安全泛化。
  - 需要人工內容判斷。
- 若是可泛用修復規則，不要只修單本 EPUB 或工作檔；必須先寫進
  `epub3itizer`，補最小可行 regression test，更新 `README.md` 或相關
  使用說明，更新 `CHANGELOG.md`，執行 `pytest -q`，再回到書庫流程重跑。
- 只有明確是單本書特有破損、不安全批次套用、或需要人工內容判斷時，
  才允許做單本手工修復或保留失敗，並在外部批次摘要中寫清楚原因。

## 提交與推送前檢查

每次提交或推送前，至少確認：

1. 本次變更範圍清楚，沒有夾帶無關檔案。
2. `pytest -q` 至少跑過一次；如果測試失敗，先修正再提交。
3. `README.md` 與實際行為一致。
4. 若有新增或變更發版說明，內容要對得上這次變更。
5. 不要把 `epubCheck` 寫成轉換流程中的強制依賴。

## 發版原則

- 專案以原始碼發版為主。
- 若要加 release notes，放在專案既定位置，並保持內容能對應版本或日期。
- 沒有明確需求時，不要硬加二進位產物。

## 已知重點

- 這個專案的價值在於穩定的 EPUB2 -> EPUB3 轉換，而不是額外包一層檢查工具。
- 轉換邏輯要以可讀、可測、可維護為優先。
- 若修改會影響 `epubCheck` 通過率，請在程式註解或 README 裡交代原因。
