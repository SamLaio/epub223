# Change Log

## 2026-07-17

- OPF metadata 清理新增移除私有 `<meta property="hdf">`，避免部分 EPUB 內殘留 HyRead/DRM 相關私有 metadata 時觸發 EPUBCheck `OPF-027`。
- CSS sanitizer 新增移除 `text-combine-horizontal: all;`，避免舊排版或閱讀器私有樣式造成 EPUBCheck / 閱讀器相容性問題；既有 `calibre_bookmarks.txt` 實體檔與 manifest 項目清理規則維持啟用。

## 2026-07-13

- 抽離可重用的 EPUB 修復流程到獨立模組 `epub3itizer.repair`，讓單獨修復與 EPUB2 -> EPUB3 轉換後的後處理共用同一套規則。
- CLI 新增 `--repair-only`，可直接對單一 EPUB 或整個資料夾套用修復流程，不必先做 EPUB2 -> EPUB3 轉換。
- 轉 EPUB3 的主流程改為呼叫共用修復管線，避免轉檔與修復邏輯分叉。

## 2026-07-13

- 補強 agent 慣例：任何需要 Codex 介入的 EPUB 修復，必須先分類為可泛用修復、單本書特有破損、不安全泛化或需要人工內容判斷。
- 明確規定可泛用修復不得只停留在單本 EPUB 或工作檔，必須寫回 `epub3itizer`、補 regression test、更新 README 或相關說明、更新 `CHANGELOG.md`，並執行 `pytest -q` 後再回到書庫流程重跑。
- 新增可選簡轉正參數 `--convert-chinese s2tw`，沿用 `metaFinder` 的 `OpenCC("s2tw")` 與自訂替換檔做法；預設仍為 `none`，不會自動改動書內文字。
- 簡轉正會處理 XHTML、OPF、NCX、XML 的可讀文字與 `title`、`alt`、`content` 等文字屬性，並避開 `href`、`src`、`id`、CSS、URL 與 script/style 內容。
- 自訂替換會在 OpenCC 轉換前後各套用一次，讓簡體 key 與正體 key 都能命中，例如 `实时` 可正確轉為 `即時`。
- 新增回歸測試，覆蓋簡轉正 CLI 參數、OpenCC 與自訂替換、以及不改連結路徑的行為。

## 2026-07-12

- 修正 OPF package `prefix` 漏宣告 `calibre:` 的問題；當 manifest item 使用 `calibre:title-page` 等屬性時，轉換器會自動補上 `calibre: http://calibre.kovidgoyal.net/2009/metadata`，避免 EPUBCheck `OPF-028`。
- 同步讓轉換器在需要時宣告 `media: http://www.idpf.org/epub/vocab/overlays/#`，避免後續 Media Overlays metadata 產生同類 prefix 錯誤。
- 新增回歸測試，覆蓋 `calibre:title-page` 的 package prefix 輸出。
- CLI 啟動時會將 stdout / stderr 切到 UTF-8，避免路徑含變音符號或其他 Unicode 字元時，最後一行 `Output written to ...` 因 `cp950` 編碼失敗而誤報。

## 2026-07-11

- 強化剩餘 EPUB2 轉 EPUB3 的 EPUBCheck 修復：
  - inline `style` 會移除 `file:///`、`res:/`、遠端 `http(s)://` 的 `url(...)` 宣告，避免 Sigil 暫存路徑或遠端資源造成 `RSC-030` / `remote-resources` 錯誤。
  - CSS 會移除破損的 `@namespace` 單行宣告，例如只剩 `@namespace h "http:` 的半截字串。
  - XHTML 表格中直屬 `<col>` 會自動包進 `<colgroup>`；若 `table` 直屬內容已混入 `div` 等壞結構，會保守降級成一般 `div`。
  - 會移除 `times` / `new` / `roman` / `serif` / `tooltip` 等由字型或網站工具誤拆出的非法 XHTML 屬性。
  - 會移除 Vue/Docsify 類網頁匯出殘留的 `v-*` 屬性，以及 EPUB XHTML 不接受的 `download` 屬性。
  - `colspan` / `rowspan` 只保留在 `td` / `th`，若誤出現在 `span` 等元素上會移除。
  - OPF metadata 會移除 EPUBMerge/Calibre 合集常見的空 `meta refines`、空 `belongs-to-collection`、指到不存在目標的 `#series` refine，並修復空或格式不合法的 `dcterms:modified`。
  - CSS 會移除被截斷的 `data:` URL 宣告，例如未閉合的 `background-image: url("data:image/...`。
- 強化第四批 500 本轉換的 EPUBCheck 修復：
  - 舊 XHTML 標籤 `<tt>` 會改為 `span`，`title_...` 這類轉檔殘留自訂標籤會改為 `div`。
  - 孤立的表格結構元素如 `tr` / `td` / `th` 若不在合法表格父層中，會降級成一般 `div` 或 `span`，避免目錄頁把 table row 直接塞進 span 時驗證失敗。
  - 畸形 ruby 若在 `rt` 後直接夾入正文而不是合法 `rp`，會扁平化為一般文字，保留正文並移除 `rt` / `rp`。
  - 會移除 `blockquote` / `q` 等元素上的舊式 `cite` 屬性，避免 `cite="輸入url"` 被當成缺失資源。
  - 會移除誤寫在 XHTML 元素上的 `body` 屬性，例如 `<blockquote body="">`。
  - OCR 或舊轉檔殘留的假標籤 `<order>` / `<do>` / `<mi>` / `<so>` 會改為 `span`，`<a___>` / `<b___>` 這類字母加底線的假標籤也會改為 `span`。
  - 由假標籤轉為標準標籤時，會移除 `of=""` / `the=""` / `zenith=""` 這類由文字碎片誤解析而來的非法屬性。
  - CSS 會將全形冒號 `：` 正規化為半形 `:`，修復 inline style 中常見的中文輸入法污染。
  - 空白或不含 `<svg>` 的 SVG 檔會從 OPF manifest 移除並刪除，後續引用修復會移除失效圖片引用。
  - `cover_page.xhtml` 若被標成 `linear="no"`，會改回主線閱讀，避免 EPUBCheck 回報 non-linear cover 不可達。
- 強化第三批 500 本轉換的 EPUBCheck 修復：
  - CSS 會移除舊工具留下的 `//` 單行註解、修復 `font-family` 中間誤寫的分號，並移除任意位置多出的孤立右大括號。
  - CSS 若 `//` 註解尾端夾帶右大括號，會保留該括號；若移除註解後下一個 selector 誤落在未閉合區塊內，會補回區塊閉合。
  - CSS 會修復 `color-#b49c84;` 這類把冒號誤寫成連字號的顏色宣告。
  - XHTML 會移除空表單控制項，例如閱讀器 CFI 用的 `<form><input type="hidden">`，避免 EPUBCheck 要求 `scripted` property。
  - XHTML 會將非標準 `<debagame>` 改為 `div`，移除壞掉的 `a=""` 屬性，並把 heading/inline 內容中的 `<hr>` 降級成可驗證的 `span` 分隔線。
  - XHTML 會移除舊式 table `summary` 屬性，避免 EPUB3 XHTML 屬性驗證失敗。
  - XHTML 解析前會逃逸正文中形似 XML 的中文假標籤，例如 `<我在明末有套房/>`，避免被當成非法元素。
  - OPF 清理會移除 EPUB3 不允許的舊式 `dc:*` 屬性與 `meta scheme`，例如 `dc:identifier scheme`、`dc:contributor role`。
  - OPF 清理會移除多看私有 `duokan-page-fitwindow` / `duokan-page-fullscreen`，不論它出現在 manifest item、itemref 屬性或 properties token。
  - 若舊 OPF 把 `spine` 誤放在 `manifest` 內，或轉換後 spine 空掉，會移回正確位置並依 XHTML manifest 補出主閱讀順序。
  - 官方 `nav.xhtml` 會依最終 OPF spine 再清一次，連到非 spine XHTML 的項目會降級為純文字，並移除空的 `ol`。
  - 官方 `nav.xhtml` 若 TOC 被過濾到沒有任何 `li`，會用第一個 spine 項目補 fallback；空的 landmarks nav 會移除。
  - 轉換流程收尾會在最後一次 OPF manifest/spine 清理後，再跑一次官方 nav 清理，確保 nav 使用最終 spine 狀態。
  - 轉換流程收尾會重新清理所有 CSS，涵蓋後段才補進 manifest 的 CSS 檔，避免殘留 `res:///` 或 `file:///` 裝置字型引用。
- 強化本批 EPUB2 轉 EPUB3 的 EPUBCheck 修復：
  - NCX 解析會跳過註解與 processing instruction 等非元素節點，避免舊書目錄檔造成轉換中斷。
  - 固定版型 `pre-paginated` XHTML 若缺 viewport，會依頁面第一張圖片尺寸補上 `meta name="viewport"`。
  - CSS 會移除 EPUBCheck 不允許的 `direction` 屬性，並正規化舊 IE 星號 hack，例如 `*font-size`。
  - CSS 會將誤寫的全形百分號 `％` 正規化為半形 `%`，避免尺寸值被 EPUBCheck / 閱讀器解析失敗。
  - OPF spine 中 cover/titlepage XHTML 若被標成 `linear="no"`，會改回預設主線閱讀，避免 non-linear content 不可達。
- 強化後續 500 本批次轉換的 EPUBCheck 修復：
  - 將舊式 `switch` / `case` / `default` 與 namespaced `epub:switch` / `epub:case` / `epub:default` 扁平化為一般 XHTML `div`，避免缺 `required-namespace` 或元素不合法。
  - 清理 iframe/audio 等舊工具輸出的私有屬性，例如 `marginwidth`、`frameborder`、`activestate`、不適用的 `placeholder`。
  - 同步 XHTML 根節點的 `lang` 與 `xml:lang`，避免兩者值不一致。
  - 將 `pre` 內不合法的 block 標題元素轉為 inline，避免 EPUBCheck 結構錯誤。
  - XHTML 內嵌 `<style>` 也會套用 CSS sanitizer，移除遠端或裝置字型引用。
  - CSS 會修復孤立 `!important`、多餘分號與破損註解造成的孤立宣告區塊。
  - BMP 轉 PNG 會偵測實際檔案內容，不只依副檔名；副檔名偽裝為 `.jpg` 的 BMP 也會轉換並改寫引用。
  - 移除不支援的 EMF/WMF 圖片引用與 manifest 項目，避免 foreign resource 缺 fallback。
  - OPF spine 中指向 `nav.xhtml` 的 itemref 會移除，即使 idref 不是 `nav`，避免 non-linear nav 不可達。
  - 無 namespace 的 HTML 文件會提升為 XHTML 預設 namespace，避免 EPUBCheck 回報空 namespace 元素不合法。
  - 遠端 iframe 廣告引用會移除，避免 remote resource 需要 OPF 宣告。
  - 孤立或缺少 `src` 的 `source` 元素會移除，避免 audio/video 外層結構不合法。
  - 修復 recover parser 後 `<meta>` 誤包住 `<link>` / `<title>` 的 head 結構，並將 head 中誤轉成 `span` 的標題還原為 `title`。
  - HTML 文件若缺少 `body`，會自動補上空 `body`，避免只有 head/title 的短頁面無法通過 EPUBCheck。
- 強化第二批 500 本轉換的 EPUBCheck 修復：
  - 空 `id` 屬性會移除，避免 `id=""` 不符合 XML token 規則。
  - `lang` / `xml:lang` 會正規化異體破折號，空或不合法語言碼會回補 `zh-Hant`。
  - 非標準 inline 標籤 `<r>` 會改為 `span`，誤入 XHTML 內容的 `<spine>` 會改為 `div`。
  - 壞掉的屬性名 `clasＶs` 會在解析前修正為 `class`。
  - 畸形 ruby 若含空 `rt`，會保守扁平化並保留可讀文字，避免 EPUBCheck 要求 `rp` 位置時失敗。
  - 移除事件處理屬性，例如 `oncontextmenu`，避免輸出 EPUB 需要 `scripted` property。
  - CSS 會移除孤立右大括號，並在缺少右大括號時自動補齊。
  - 空 NCX 會視為沒有 TOC，不再讓轉換流程因 `NoneType` 中斷。
  - 從 OPF `spine` 誤入 XHTML 的屬性如 `page-progression-direction`、`toc` 會移除。
  - `@font-face` 清理後若殘留孤立右大括號，會一併移除。
- 修正 CSS 檔案開頭殘留孤立宣告區塊，例如 selector 被清掉後剩下
  `font-weight: bold; }`，避免 EPUBCheck `CSS-008`。
- 清理 XHTML `head` 中誤放的 block 元素，例如頁面分隔用 `div`，避免
  EPUBCheck 判定 `head` 結構不合法。
- 清理空的 OPF `meta property="role"`，避免 refines 角色 metadata 沒有
  內容時造成 EPUBCheck 失敗。
- 強化 CSS 修復：移除註解後多餘分號、將 `width=100%` 這類誤寫轉成
  `width: 100%`、移除空宣告如 `font-family: ;`，並把遠端 `url(http...)`
  改成 `none`。
- 若環境有 Pillow，會將 EPUB 內的 BMP 圖片轉成同名 PNG 並改寫引用，
  避免 EPUB3 foreign resource 缺 fallback 的錯誤。
- 清理 OPF 中空的 `ibooks:*` meta，例如 `ibooks:version` 與
  `ibooks:specified-fonts`，避免未宣告 prefix 與空內容造成 EPUBCheck
  失敗。
- 修正 CSS 宣告尾端殘留反斜線，例如
  `border-bottom: ...;\`，避免 EPUBCheck `CSS-008`。
- 修正末端 XHTML 正規化誤刪官方 nav `epub:type="toc"` 的問題；現在只會移除
  無 namespace 的舊式 `type` 屬性，保留 EPUB3 nav 必要的 `epub:type`。
- 修正壞掉的 XHTML namespace，例如 `http://www.w3.org/十九99/xhtml` 這類
  OCR/轉碼污染，會正規化回標準 `http://www.w3.org/1999/xhtml`。
- 轉換流程末端新增一次全 XHTML 結構正規化，確保移除舊 TOC 連結、
  修復 nav 或其他後處理之後，仍會清掉表格內空 `span` 等 EPUBCheck
  結構錯誤。
- 放寬表格空 `span` 清理，不再要求元素帶 XHTML namespace，避免舊 HTML
  轉檔後 `<table><tr>...</tr><span/><tr>...</tr></table>` 仍被 EPUBCheck
  判為結構錯誤。
- 移除多看/掌閱圖庫常見的私有 `gallery` 屬性，保留原本 `div` 與圖片內容，
  避免 XHTML 屬性驗證失敗。
- 修正 EPUBCheck 後續發現的表格與 EPUB switch 殘留問題：移除
  `table` / `tr` 等表格結構中空的 `<span/>`，並將孤立的
  `<case>` / `<defaultcase>` 正規化為 `div`，同時移除
  `required-namespace` 屬性，避免 XHTML 結構驗證失敗。
- 強化 OPF metadata 清理：移除 `dc:builder`、`dc:builder_version` 等
  EPUB/DC 規範未定義的 metadata 元素，但保留並轉換可修復的 `dc:meta`。
- 強化 CSS 修復：清除 CSS 檔案開頭或內容中的 ASCII 控制字元，避免
  EPUBCheck `CSS-008`；CSS `url(...)` 若引用不存在的資源，會先嘗試用
  書內同名資源改寫，找不到時改為 `none`，保留其他背景設定。
- 修正 OPF manifest 去重時可能誤刪 `meta name="cover"` 指向的 cover
  item：現在同一路徑重複時會優先保留 cover metadata 或 `cover-image`
  property 指向的項目，避免封面 metadata 變成懸空引用。
- 調整轉換流程末端，在移除舊 TOC 連結與清理官方 nav 後，會再執行一次
  XHTML 引用修復、補 manifest 與 OPF 清理，確保最後打包進 EPUB 的內容
  不會保留後續流程產生或漏掉的壞連結。
- 依照目前書庫轉換失敗案例，擴充 EPUBCheck 後續修復：當 `dl` 已混入
  `div`、裸文字或其他無法安全保留語意的子層時，改採 Sigil/calibre
  式保守修復，將整個區塊扁平化為 `div`，保留文字內容但避免 EPUB3
  定義列表結構錯誤。
- 修正 XHTML 連結直接指向圖片資源造成 EPUBCheck `RSC-010` 的問題：
  轉換後會將這類 `<a href="...jpg/png">` 改為非連結 `span`，並保留原本
  的文字或內嵌圖片。
- 強化官方 `nav.xhtml` 清理：若修復流程移除失效 href 後留下只有
  `span`、沒有子 `ol` 的目錄 leaf，會自動移除該 leaf，避免 EPUB3 nav
  結構出現 `li` 缺少必要內容的錯誤。
- 修正 OPF 位於 `OEBPS/content.opf` 時，manifest href 誤寫成
  `OEBPS/cover.jpg` 的情境：現在會先轉成 package 相對路徑 `cover.jpg`
  再用解析後路徑去重，避免 EPUBCheck 誤判引用 `OEBPS/OEBPS/cover.jpg`
  未宣告。
- EPUB3 轉換後會移除舊 EPUB2 `toc.ncx` manifest 項目、實體檔與
  spine `toc` 屬性，改以產生的 `nav.xhtml` 作為標準目錄，避免舊 NCX
  殘留錯誤路徑被 EPUBCheck 驗出。
- EPUB3 OPF 清理會移除舊 `<guide>` 區塊，避免 EPUB2 guide 中的壞
  fragment 造成 EPUBCheck `RSC-012`。
- 強化 XHTML 清理：移除 `head` 直屬文字與子元素 tail 中的非 XML
  whitespace，並移除包含底線的不合法屬性名稱，例如 `text-align_`。
- 進一步擴充 EPUBCheck 失敗後的自動修復：移除全形問號形式的假 XML
  宣告，將 `html` 根節點中誤落在 `body` 後的內容搬回 `body`，清理
  `dl` 開頭不合法的 `dd`，並移除所有元素上 EPUB3 不允許的 `target`
  屬性。
- 修正 NCX 仍保留已被過濾掉的舊連結問題：轉換流程現在會在 TOC
  對照 final spine 後重新寫回 `toc.ncx`，並移除 TOC/guide 中不安全的
  fragment，避免 EPUBCheck 的缺檔與不存在錨點錯誤。
- 強化 OPF manifest 路徑清理：當 OPF 位於 `OEBPS/content.opf` 且 href
  誤寫成 `OEBPS/cover.jpg` 時，會修成以 OPF 為基準的 `cover.jpg`，
  並以解析後 package 路徑去重。
- 強化 inline style 清理：移除混進 style 的非 CSS 宣告，例如
  `class=`，並補齊缺右括號的 `url(...)`。
- 只保留一個 `meta property="dcterms:modified"`，避免 EPUBCheck 因
  EPUB3 修改時間 metadata 出現多次而失敗。
- 依照 calibre Editor「Check book」可自動修復的方向，擴充 EPUBCheck
  失敗後可重用的結構修復：清理 `head` 內誤留的裸文字、將不合法的孤立
  `li` 改為段落、將 `ul` / `ol` / `menu` 直屬非清單元素改為 `li`，並
  移除或轉換 body 內誤放的 `meta` / `style` / `title`。
- 修正缺 `href` 的 `a` 在引用修復後仍留作非法 anchor 的問題：若連結
  目標或 fragment 無法安全解析，會移除 `href` 並改成 `span`。
- 強化 OPF 清理：移除 manifest/itemref properties 中的
  `duokan-page-fullscreen`，並將只有日期文字的 `opf:meta` 轉為 EPUB3
  合法的 `meta property="dcterms:modified"`。
- 修正無 namespace XHTML fallback 會寫入非法 `xmlns:epub` 屬性的問題。
- 擴充 CSS 清理，修復舊檔中選擇器被多插入數字造成的 EPUBCheck CSS
  解析錯誤。
- 擴充 EPUBCheck 後續修復流程中發現的 XHTML 正規化：修正大寫 XHTML
  標籤、`PUBU` / `spen` 等非標準或錯字元素，移除 `base`，將無 `href`
  或巢狀的 `a` 改為 `span`，移除不合法 `name` / `cid` / `value` 屬性，
  並將 HTML5 尺寸屬性中的非整數值移到 CSS `style`。
- 修正原始檔含異常 namespace 屬性導致轉換程式失敗：解析 XML 前會
  正規化常見錯誤 namespace，例如 XHTML `https` / `/epub`、OPF
  `/v3`、DC `elements/1.0/`，並移除非法 `xmlns:xmlns` 與錯誤
  `xmlns:xml` 宣告；OPF 進入轉換器前也會套用同一套修復。
- 擴充「被引用資源未在 OPF manifest 宣告」的自動修復：除了
  `href` / `src` 與 CSS `url(...)`，也會掃描 `poster`、`data`、
  `srcset`、SVG `xlink:href` / `href` 以及 CSS `@import`，若檔案實際
  存在但未宣告，會自動補進 manifest。
- 修正 OPF metadata 缺少 EPUB 必填 `dc:title` / `dc:language` 的問題：
  若缺少或內容空白，會補入 fallback `Untitled` 與書庫慣例語言
  `zh-Hant`，避免 EPUBCheck 因必要欄位缺失失敗。
- 移除 OPF manifest `item` 上的多看閱讀私有屬性
  `duokan-page-fullscreen`，避免 EPUBCheck 因未定義屬性失敗。
- 修正 OPF spine `itemref` 的不合法 `linear-type` 屬性：值為 `yes` /
  `no` 時會改成 EPUB 標準 `linear`，非法 `linear` 值會移除，避免
  EPUBCheck 因未知屬性或不合法值失敗。
- 修正 XHTML 廢棄 `<strike>` 元素造成的 EPUBCheck 錯誤：轉換時會改成
  HTML5/EPUB3 合法的 `<s>`，保留原本刪除線語意與內容。
- 修正 XHTML `ruby` 結構缺少 `rp` 的 EPUBCheck 錯誤：`ruby` 直屬
  `rt` 前後若缺少 fallback，會自動補入 `<rp>(</rp>` 與 `<rp>)</rp>`；
  已存在的 `rp` 不會重複加入。
- 修正 XHTML `dl` 結構不合法：`dl` 直屬裸文字會包成 `dd`，直屬
  `p`、`span`、`div` 等非 `dt` / `dd` 元素會改成 `dd`，避免 EPUBCheck
  因定義列表子層不合法失敗。
- 強化 NCX uid 同步：若 `toc.ncx` 缺少 `dtb:uid` meta 會自動補上，且
  轉換流程會在 OPF 最終清理後讀回 `unique-identifier` 對應的
  `dc:identifier` 值，再同步到 NCX，避免 NCX uid 與 OPF uid 不一致。
- 修正 XHTML `<meta>` 缺少必要 `content` 的 EPUBCheck 錯誤：`viewport`
  會從舊式 `width` / `value` 屬性搬到 `content`，缺內容的
  `Content-Type` 會改成 `<meta charset="utf-8"/>`，其他無法安全判斷且缺
  `content` 的 `name` / `http-equiv` meta 會移除。
- 修正 OPF metadata 內不合法的 `dc:meta`：轉成 EPUB3 合法的
  `<meta>`，並將常見 `opf:property` / `opf:name` 這類屬性命名空間改為
  普通 `property` / `name` 屬性，避免 `dcterms:modified`、cover metadata
  等項目因 `dc:meta` 結構被 EPUBCheck 擋下。
- 調整 `hr align="center"` 的 CSS 轉換為 `margin: 0 auto`，讓寬度不是
  100% 的水平線也能正確置中。
- 擴充 XHTML 舊式尺寸屬性修復：當 `width` / `height` 出現在 EPUB3
  不允許該屬性的元素上時，會轉成 CSS `style`；純數字會視為 px，百分比
  與常見 CSS 長度單位會保留，無法安全判斷的值才移除。
- 修正 XHTML 舊式呈現屬性的 EPUBCheck 問題：`hr size` 會轉成 CSS
  `height`、`border`、`background-color`，`hr align="center"` 會轉成左右
  `auto` margin；其他不合法的 `size` 屬性會移除，避免 EPUB3 驗證失敗。
- 修正 NCX/nav/guide 連結到錯誤資料夾或副檔名時的處理：TOC、page-list
  與 guide/landmarks 會先比對 final spine，若原目標不存在或不是 spine
  項目，會用同檔名、同 stem、`.html`/`.xhtml` 等候選規則反查實際 spine
  檔案；仍無法對應時才移除該 nav/toc 連結，避免 EPUBCheck 的非 spine
  目標錯誤。
- 轉換後清理會移除 EPUB 內的 JavaScript：刪除 XHTML `<script>` 元素、
  移除 manifest 中 `.js` 或 JavaScript media-type 項目，並刪除 package
  內殘留的 `.js` 實體檔，避免 EPUB3 驗證與閱讀器相容性問題。
- 移除 calibre 閱讀器寫入 EPUB 的書籤檔
  `META-INF/calibre_bookmarks.txt`，包含 manifest 項目與未列入 manifest 的
  實體檔。
- 參考 calibre Editor「Try to correct all fixable errors automatically」的修復
  方式，擴充轉換後的 OPF/XHTML 清理：自動修正非法或重複的 XML id、
  將 body 內裸文字包成段落、移除沒有 href 的 manifest 項目、去除重複
  manifest href 與重複 spine idref、移除 spine 的 `linear` 屬性、清掉空的
  `dc:identifier`，並在 OPF 缺少有效 `unique-identifier` 時自動補 UUID。
- 轉換後若 spine 項目副檔名本來就是 HTML/XHTML，但 OPF media-type 錯誤，
  會保守修正為 `application/xhtml+xml`，避免 EPUBCheck 將文字內容判為非
  HTML spine 項目。
- 修正缺少被引用資源時的自動尋找邏輯：若 XHTML、CSS 或 OPF 指向
  `OEBPS/Images/cover.jpg` 這類不存在路徑，轉換器會先以檔名、stem、
  資源類型與副檔名反查 EPUB 包內實際檔案，例如改指向根目錄的
  `cover.jpeg`，或改到實際存在的 CSS/HTML/圖片位置；找不到替代檔時才
  移除或保留失敗。
- 擴充缺圖修復到 SVG `<image href>` / `xlink:href`，處理封面頁常見的
  `../Images/cover.jpg` 實際應指向 `../../cover.jpeg` 的狀況。
- 新增針對畸形 EPUB2 來源的 EPUBCheck 修復：可用 recover parser 讀取破損
  XHTML/NCX，修正 OPF/NCX XML ID 與對應 spine 參照，移除或提升舊 XHTML
  `type` 屬性，讓重複元素 ID 唯一化，修正巢狀 XHTML 指向 package root
  圖片的連結，將 nav/page-list 過濾到 spine 資源，並依檔案內容偵測圖片
  manifest media type。
- 擴充 XHTML 與連結清理：移除舊 content nav、body、anchor 元素上的
  舊式 `type` 屬性，recover 修復畸形 `br` / `img` 標記，將包住 block
  list 的段落改成 `div`，並改寫大小寫與實際 package 檔案不同的本機連結。
- 新增轉換後最終引用清理：大小寫路徑修復後重新讀取 OPF，移除缺失圖片、
  清掉指向缺失檔案的壞連結，並移除本機 anchor 中不存在的 fragment。
- 依解析後的 TOC 資料重建畸形 NCX，並移除舊 landmarks self-fragment 連結，
  避免 EPUBCheck 將其視為指向非 spine 內容的引用。
- 會將已存在但缺少 OPF manifest 宣告的被引用資源補進 manifest，包括
  XHTML 內容引用的圖片檔。
- 轉換後清理 OPF manifest：移除缺失 manifest 檔案、刪除已移除項目的
  spine itemref、依副檔名修正 media type、去重 `properties="nav"`，並重建
  NCX 以避免重複目標造成 playOrder 衝突。
- 以 NCX 檔案位置為基準解析 NCX 目標，percent-decode 後再比對 TOC/page-list
  連結與 spine 路徑，移除缺失 stylesheet/script 引用與缺失 same-page
  fragment，並優先保留依檔案內容偵測出的圖片 MIME type。
- 避免 NCX 目標已含 package 目錄時被重複加上前綴；當來源 TOC 項目全部被
  過濾時，會輸出結構正確的空 nav TOC。
- 重建 NCX 時，`content src` 會以 NCX 檔案為基準寫入；空 nav TOC 會補
  fallback `li`，並在 OPF `properties="nav"` 去重時優先保留產生的
  `nav.xhtml` 項目。
- 當來源 TOC 項目全部被過濾時，產生的 nav TOC 會指向第一個 spine 項目，
  而不是輸出只有文字的 fallback 項目。
- 移除常見非標準 XHTML 屬性，清掉非產生版 EPUB3 nav 的舊 TOC/nav 連結，
  並移除 nav 或非 XHTML 資源上殘留的 `scripted` manifest property。
