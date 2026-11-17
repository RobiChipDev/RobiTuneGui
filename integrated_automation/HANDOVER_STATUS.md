# v0.3.29 最新狀態

修正電供開埠等待與逾時，補充查詢失敗診斷。現場唯讀識別成功，本版實機待驗證；詳見 RELEASE_v0.3.29.md。以下為歷史紀錄。

# v0.3.28 最新狀態

電供可獨立待命監看，CH2 改為選用開關；詳見 RELEASE_v0.3.28.md。125 項測試：119 通過、6 GUI 跳過。TA612C 未接入，48 V 韌體與實機驗證未完成。本版未操作硬體。以下保留歷史紀錄。

# Robi 專案交接狀態與後續工作基準

- 更新日期：2026-11-10（Asia/Taipei）；目前交付 **Robi v0.3.27**，以正式 .26 為基準，保留 .26 ZIP。
- 本次完成螺旋槳自動排序、另存新檔及複製名稱按鈕；依最新決策取消 Pair。未改 PID／通訊／換算／實驗流程，未操作硬體或修改韌體。
- 最終回歸 119 項：113 通過、0 失敗／錯誤、6 GUI 跳過；不能視為 Windows GUI 或硬體驗收。
- Windows GUI／DPI、PID／PLL 實機仍待驗證；48 V 工作本次暫停，公司端後續進度須核對新工程與燒錄紀錄。
- 第 1–18 節為 .22–.26 歷史；第 19 節為目前 .27。歷史「本次」只指當時工作。
- EXPERIMENT_INDEX／原始實驗未變：49 筆資料夾、17 組唯一測次；本次無新增量測。

## 1. 證據與讀取範圍

| 來源 | 已完成的工作與限制 |
|---|---|
| 02_PROJECT_MEMORY.txt | 前次完整閱讀，128 行；歷史觀察與工程背景來源 |
| 03_VERIFIED_SOURCE_REFERENCE.txt | 前次完整閱讀，2,528 行；17 個收錄檔案區段與 ZIP 對應檔案一致（比對忽略首尾空白） |
| Robi_Integrated_Automation_v0.3.22.zip | 前次解壓檢查，共 46 個檔案；ZIP CRC 無錯誤；全部 Python 檔案通過語法解析 |
| history_documents.zip | 已解壓並逐份完整閱讀 12 份 Markdown；ZIP CRC 無錯誤；完成與 v0.3.22 相關原始碼的靜態對照，詳見第 11 節 |
| 歷史實機資料 | 已讀取 8 個實驗 ZIP、49 筆資料夾的全部 245 個五檔輸出，去重為 17 組；逐筆路徑、metadata、事件與雜湊見 EXPERIMENT_INDEX.md／.json；未重算歷史分析數值，現場截圖及外部完整 log 仍缺 |
| STM32 工程與硬體 | 已解壓 RC100D_Rum3848yMotorTest.zip（1,646 檔），核對相關設定、通訊程式及附帶 ELF／map，見第 13 節；板上實際版本及硬體規格原件仍待核實 |

app.py 介面與 controller.py 量測 JSON 的版本標示皆為 0.3.22。這是交接檢查，不是全面程式碼審查或硬體驗收。

證據分類：
- **程式確認**：已讀取原始碼可確認的行為。
- **工具測試**：實際執行的離線檢查，須附範圍。
- **歷史記錄**：交接文件或使用者轉述，不能當成本次重現結果。
- **待驗證**：尚無充分實機或資料證據。

## 2. 合作與修改原則

- 使用繁體中文及具體工程語言，保留必要英文參數名稱，數值附單位與來源。
- 「先討論／不要生成」先確認方案；「做／來吧」才依授權完成修改、對應測試及交付。
- 先核對當輪原始 CSV、data.json、log、對應程式版本及截圖，再診斷；不假裝已讀、已改、實測或燒錄。
- 維持既有架構，採完成需求所需的最小修改；交付保留可回復版本，交代已測與未測範圍。
- 白底、整齊、專業、重要參數大字；原量測小字在旁；測試按鈕與設定按鈕分區；任務與時間進度同列，盡量單屏，不大幅重排 UI。
- 區分讀值保留、資料過期、通訊失敗、負號、漂移與真實推力；不以絕對值、自動重歸零或平滑補值掩蓋異常。
- 7100 rpm 是軟體上限，不是機械安全轉速；口頭「50 V／30 A」不足以決定 48 V 過壓門檻。

## 3. 系統分工與通訊

Robi 是 Python／Tkinter 命令、流程與資料記錄端。即時 FOC、電流迴路、速度迴路及 Observer／PLL 在 STM32 執行。馬達由單一 Controller 擁有通訊；感測器各有自己的 worker 與連接埠，正式 CSV 由 Controller 寫入。

| 設備／項目 | v0.3.22 預設或實作 |
|---|---|
| 馬達 | COM5、1,843,200 baud、MCP v2／ASPEP、Motor ID 1 |
| 力規 | COM6、9,600 baud、8N1、站號 1、HH-LL、每組間隔 0.1 s |
| 力規讀取 | Modbus RTU function 03；450／452 各兩個暫存器；signed int32；CRC16 Modbus |
| 電供 | 預設停用；SERIAL、115,200 baud、resource 空白、通道 [1]、間隔 1 s |
| 電供 adapter | 檢查 GPP-6030 型號；僅允許查詢，不設定電壓／限流、不控制輸出開關 |
| Iq／Id | 每次馬達連線讀 SCALE_CONFIG，使用板端 current 係數換算 A/count |
| 外接溫度 | 線圈 T2／環境溫度尚未接入；板端溫度不能直接代表線圈、力規或 MCU 內部溫度 |

首次開啟為實機鎖定／模擬。模擬提供明示的馬達模擬回授，不開實體感測器埠，不偽造力規／電供量測。馬達連線後自動開始已啟用的力規監看，亦可獨立監看力規；監看與正式記錄分開。

歷史電供操作：CH1 馬達 24 V／3 A、CH2 力規 10 V／1.5 A，兩路獨立。這與力規 CH1／CH2 是不同通道系統，亦不是通用額定值。

## 4. 量測、方向換算與歸零

| 力規通道 | 預設用途 | 倍率 | 原始零點 |
|---|---|---:|---:|
| CH1 | 推力 | 0.01 N/count | 0 count |
| CH2 | 扭矩 | 0.001 N·m/count | 0 count |

原量測 = (raw count − 軟體零點) × 倍率。用途可設定，不永久硬編碼。歷史 CH2 倍率 100 已被後續要求取代，但載入舊 JSON 仍尊重其明確倍率，須人工核對。

| 安裝／槳葉標示旋向 | 推力係數 | 扭矩係數 |
|---|---:|---:|
| 正裝 CW | −1 | −1 |
| 正裝 CCW | −1 | +1 |
| 反裝 CW | +1 | −1 |
| 反裝 CCW | +1 | +1 |

反裝 CW 是已同意的台架約定，仍待實測。係數依裝法與槳葉標示旋向推定，未獨立讀取實際旋向。任一項未知時保留原量測方向。整段相乘並保留過零／負值。

- 大字、即時曲線與 HTML 套用方向係數；7 pt「原量測」已扣零點並乘倍率，並非 raw count。
- CSV、summary、stages 保留方向換算前量測；JSON 保存 direction_factors；舊資料缺係數時不猜測補正。
- 歸零逐通道更新 zero1／zero2，不發硬體歸零命令，實體面板不隨之改變。
- 歸零要求 REAL 馬達連線、無故障 IDLE、回授 0 rpm、未記錄、力規 reading。
- 最近 1.5 s 至少 3 筆，跨度 ≥0.5 s，最新樣本距今 ≤0.5 s，原始 count 最大差 ≤2 count。2 count 為程式選值，尚非正式驗收規格。
- 儲存並於後續載入裝置設定才能重用零點；現行啟動未自動載入 device.json。硬體面板另行歸零後須重新核對軟體零點。
- 未實作獨立斷電歸零模式。

## 5. 實驗流程與重要參數

| 參數 | 預設 |
|---|---:|
| 轉速清單 | [1500, 1600] rpm |
| 最高轉速 | 7100 rpm |
| ramp_ms | 3000 ms |
| dwell_s | 10 s |
| baseline_s | 5 s |
| poststop_s | 10 s |
| reach_timeout_s | 30 s |

實際測次以當輪 data.json 為準。正式流程：preflight → baseline → starting → startup_settle → ramping／dwelling（依清單重複）→ stopping → poststop → 完成。

- 開始要求 IDLE、無故障、SPEED mode=3；啟用感測器須有有效資料；preflight 上限 12 s。
- 固定先啟動至 1500 rpm，啟動等待上限 40 s，即使第一設定點不是 1500 rpm 亦如此。
- 到速誤差 ≤max(12 rpm, 目標×1%)，連續 2 s 才切換；定速偏差 >max(60 rpm, 目標×5%) 或離開 RUN 會中止。
- 未以力規穩定度判斷切段；定時完成不代表推力量測穩定。
- 力規過期門檻 max(2 s, 3×interval)；電供 max(5 s, 3×interval)。通訊異常、故障、佇列溢出等可中止。
- 現行正常結束直接送 Stop，未增加減速停止階段；停止狀態確認最多 5 s，再記錄 poststop。軟體停止狀態不代表機械停穩。
- poststop 可提前「停止記錄」，留下 poststop_ended_by_operator；原完成／中止原因保留。結束後力規持續監看。

## 6. 設定、輸出與命名

預設 Documents/Robi，下分 ExperimentData、ExperimentSettings、DeviceSettings。現行裝置儲存固定寫 DeviceSettings/device.json；槳葉清單為 DeviceSettings/propellers.json。設定須套用才生效，正式記錄期間鎖定相關設定。

每輪預期輸出 data.csv、data.json、data_summary.csv、data_stages.csv、data_report.html。摘要／HTML 失敗會另報錯，不等於原始 CSV 未保存。CSV 是長格式原始量測與事件；JSON 保存版本、完整設定、倍率零點、方向係數、可用的板端縮放與 PID 讀回。

HTML 使用同時間軸、階段底色、長間隔斷線、縮減顯示時保留分桶極值，不平滑補值。末 30 s 只是比較窗口，不是穩定判定。Motor Pilot 回報功率不替代獨立電供 Wi，也不直接宣稱為軸端機械功率；缺測保持空白。

命名例：1050_3-Blade_30%PP_No01_CW_NormalMount_1500-5000RPM_1500-2000-2500-3000-3500-4000-4500-5000。

- 1050 是 10×5 槳葉規格，不是 1050 rpm；槳葉資料保存 dimension、blades、material、number、rotation。
- 正裝 NormalMount、反裝 FlippedMount。純降速區間由高至低；升速或混合順序由低至高；附完整轉速清單。
- REAL 不加模式及日期時間；重名 _A、_B…；SIMULATION 保留模式與時間。
- 選槳測次中止／故障標記 _Abort／_Error-…；未選槳不套用該結果重新命名分支。最終狀態以 session_end 與事件核對。

## 7. PID／PLL v0.3.22

已實作，尚未完成實機驗證。入口「裝置與螺旋槳 → PID／PLL」。

- 可寫 Speed Kp/Ki 及兩個 divisor、Iq/Id Kp/Ki、Observer C1/C2、PLL Kp/Ki；Torque Reference 為唯讀 raw，無 A 顯示或寫入。
- 寄存器元素：Speed 2/3、divisor 81/82、Iq 6/7、Id 10/11、Observer 13/14、PLL Kp/Ki 18/17、Iq Reference 37。ID=(element<<6)|0x11；GET=0x11，SET=0x09。
- divisor 顯示 128／16384，wire 傳指數 7／14。PI 0..32767；Observer signed int16；divisor 1..32768 的 2 次方。範圍合法不代表適合馬達。
- 先讀板端；單項寫入前 sample 確認無故障 IDLE／0 rpm，再讀取比對 expected；寫入後立即讀回。
- 真正寫入前設 pid_unverified 並清 snapshot；結果未確認則阻擋新實驗，直到再次成功讀取。寫入前輸入／狀態／expected 拒絕不一定設該旗標。
- 無自動回滾、無 Flash 儲存。重新連線清除 snapshot；當次已讀取 PID 後，正式測試前再讀並存 pid_board_readback。
- 舊 Speed Kp/Ki/Kd「PID 紀錄」是手動筆記，載入裝置 JSON 不自動寫板。
- 歷史截圖數值不是自動寫入預設；Observer C1 曾被截圖裁切，符號以板端讀回確認。

## 8. 已知差異與限制

| 項目 | 已確認差異／處理基準 |
|---|---|
| 自訂名稱優先 | 儲存實驗 JSON 名稱可優先；選槳測次資料夾卻由 label_override 優先於 run_name，未符合完整歷史需求 |
| 裝置儲存檔名 | 舊文件稱可選或 Device_測試台名稱.json；現行固定 device.json |
| 文件版本 | README 開頭、VALIDATION、CHANGELOG 保留 v0.3.11 等歷史說明；README 後段追加至 v0.3.22，尚未統整 |
| 符號 | CSV／summary／stages 與畫面／HTML 所處方向換算階段不同，不能直接視為同號 |
| 絕對效率欄 | stages 另有 eff_abs_gf_per_W，並保留 signed 欄位；不改寫原始推力符號，不以絕對欄掩蓋異常 |
| 歸零保存 | 儲存後須載入設定，不能宣稱重啟自動恢復 |
| 舊診斷設定 | diagnostic_1500_1600_1500.json 使用 [1500,1600,1500] rpm、上限 2600 rpm、停留 120 s、基線 30 s、poststop 60 s，且含舊 /root/Documents/RobiV03Logs 路徑；不是現行預設 |
| 歷史工程文件 | 已完成逐份閱讀與靜態差異盤點；歷史初稿保留原樣，待後續依差異更新及審查，不等於正式驗收 |

## 9. 歷史 debug、漂移與待證實原因

以下敘述仍屬歷史觀察／推測；本次已取得並索引部分對應原始測次，但未重算漂移數值、重現故障或驗證根因：

- 早期未啟動即 FAULT_OVER／0x4，先檢查故障與啟動條件。COM6 Access denied 與 FileNotFound 分別為拒絕開埠與找不到裝置；重插恢復不能證明根因。
- 保留值曾被誤認為即時值。歸零無效的一次畫面為 FAULT_NOW、VBUS 0、0x40004，符合歸零禁用條件。
- 約 6000 rpm 報錯，使用者描述撞到 3 A 限流；缺當輪電供紀錄，不能補證 CC 時序或直接歸因 PID。
- 約 3000 rpm 高頻聲、3500 rpm 振動聲，推力亂跑／負值；後續描述約 2500–3000 與 4500–5000 rpm 漂移，尚非已證實共振帶。
- No02→No01 有拆裝；No01 A/B 只有歸零、未動機構；後續 C/D 曾討論不重新歸零。槳葉歷史鎖付 0.5 N·m，其餘支架未建立完整扭力規範。
- No01_A 在 3500／4000 rpm 跨零；歷史 2600 rpm 運轉末段與停機末段差約 1.08–1.21 N，僅作診斷，不得以停機殘值直接修正真實推力。
- 未證實原因：機構共振、槳葉變形／共振、力規／變送器／溫漂、鎖付預負載、線材受力、地面效應及氣流影響。反裝仍飄或換槳後才飄，都不足以單獨排除／確認原因。
- Robi 與 Motor Pilot 讀同一估速來源，符合不是獨立驗證；約 9 Hz 紀錄不足以直接證明高頻振動。
- 「10–20 s 穩定、漂移 0.01」尚缺正式單位確認、起算點、窗口與 peak-to-peak／斜率定義。

## 10. 完成度與測試範圍

| 狀態 | 項目 |
|---|---|
| 程式已實作 | 馬達流程、力規監看、校正／歸零、方向換算、設定分離、槳葉管理、資料輸出／報告、PID／PLL |
| 歷史實機證據 | 獨立力規讀取成功；v0.3.21 啟動與讀值畫面；不足以證明全部歸零操作驗收 |
| 待實機驗證 | v0.3.22 PID 讀寫、韌體寄存器相容性、失敗／逾時／重連一致性、反裝 CW、完整 Windows GUI／DPI |
| 電供 | 唯讀程式存在，線路、回覆格式與整合實測待確認 |
| 溫度 | 外接線圈 T2／環境溫度未接入 |
| 48 V | 韌體修改、編譯及燒錄尚未完成 |
| 工程文件 | 新人訓練、四種圖、測試矩陣及交接文件已有初稿；本次閱讀與差異盤點完成，版本更新／正式審查仍有缺口 |
| 正式流程 | V1.0 尚未正式驗收；可重用 skill 尚未正式建立／安裝 |

前次交接實際工具檢查：ZIP CRC、46 個檔案可讀、全部 Python 語法解析、17 個參考區段內容比對。另執行 test_pid_settings 的 2 項 Mock 測試並通過，涵蓋 signed Observer／divisor 封包、唯讀與非法 divisor 拒絕、非安全狀態拒寫、讀回不符與重讀解鎖、成功單項寫入讀回。沒有開實體連接埠。

前次未重新執行全套測試或 GUI；本次完整讀取歷史文件、檢查相關原始碼及測試定義，未執行新一輪程式測試、GUI 或硬體測試。VALIDATION.md 的舊版 66 項（65 通過、1 跳過）與交接記憶中的新版測試描述應保留各自版本範圍，不能合併宣稱本次全套通過。離線測試不等於硬體驗收。

## 11. 歷史文件盤點結果（2026-11-04）

### 11.1 實際閱讀範圍與狀態

已解壓 history_documents.zip，逐份完整閱讀下列 **12 份 Markdown（11 組不重複內容）**。無法讀取的包內文件：**無**。歷史原件不修改；本節是對照紀錄，不將初稿升格為正式核准文件。

| 實際讀取檔案（相對 history_documents/） | 行數 | 已有內容 | 對照結果與待補 |
|---|---:|---|---|
| README.md | 41 | 交接入口、讀者導覽、來源索引、文件狀態定義 | 導覽與證據分級仍適用；明示基準 v0.3.11，應補 v0.3.22 差異；原始來源連結未於本次開啟或確認權限 |
| users/user_manual.md | 43 | 安裝、連線、8 步流程、存檔與異常排查 | 主要流程與單位仍適用；設定入口名稱過時，未涵蓋槳葉管理、四方向、軟體歸零、PID／PLL、停止記錄與新命名 |
| training/onboarding.md | 27 | 8 階段新人訓練、必答題、帶教紀錄 | 可作訓練框架；姓名、日期、帶教簽核均待填，不能宣稱已完成訓練；須補 v0.3.21／22 操作與驗收證據 |
| engineering/architecture.md | 160 | 模組責任、Class、State、Sequence、Flow 四種 Mermaid 圖及重構候選 | 主要架構仍適用；未涵蓋新模組／命令／參數狀態；部分敘述須限縮，詳下表 |
| engineering/roadmap.md | 45 | 主管白板逐項對照、分階段工程化、V1.0 候選條件、未來 AI 流程 | 需求與先補證據再重構的原則仍適用；版本與進度須同步；主管對「APIs 亂序」原意尚待確認 |
| engineering/test_matrix.md | 49 | T01–T17、測試檔定位、型別／邊界／錯序候選、結果欄位 | 對應測試檔仍存在；歷史結果僅屬 v0.3.11，未涵蓋新功能的完整驗收，詳 11.4 |
| experiments/archive_rules.md | 36 | 五檔保存、人工 metadata、照片、版本追溯、來源索引 | 保存原始值原則仍適用；REAL＋時間命名過時；人工紀錄是流程建議，未自動產生；CW 標記與後來交接說法有待原始資料核對 |
| logs/decisions.md | 24 | D01–D12 歷史決策／觀察與收尾方法 | 多數原則仍適用；D01 版本過時，D03 旋向與 D09 比較目標不能當全部現行測次設定 |
| templates/change_record.md | 25 | 需求、影響、測試、未驗證與回復方式模板 | 可沿用；是空白模板，不是已完成的變更驗證紀錄；PID 變更需另記原值／新值／讀回與狀態 |
| templates/experiment_record.md | 33 | 樣品／設備、方向視角、鎖付、校正、操作事件與停穩紀錄模板 | 可沿用；需補明確的軟體／硬體歸零、方向係數、PID 讀回、供電／限流與設定來源欄位；尚無已填樣本證據 |
| meetings/20261104_vendor_meeting_notes.md | 127 | 漂移診斷數值、假設、排查、demo、廠商問答與供樣需求 | 實際是 11/03 撰寫的 11/04 會前準備稿；不是會後紀錄，不代表已傳送或獲廠商同意 |
| vendor_meeting_preparation.md | 127 | 同上 | 與 meetings 版本逐位元相同；兩份均已讀取，不計為兩份獨立實驗／會議證據 |

history_documents 本身未含來源索引連結所指的 CSV 壓縮包、主管白板圖片或外部技術文件原件。後續補交的 8 個實驗 ZIP 現已讀取並完成測次映射，見第 14 節；主管白板與外部技術文件原件仍未取得／驗證，屬未讀取引用資料而非包內讀取失敗。未重新核算會議稿中的歷史實驗數字，也未把其中 NASA／BASF／APC 背景摘要當成當前已核實的樣品性能證據。

### 11.2 仍適用、已過時與現行差異

| 主題／歷史位置 | v0.3.22 對照與判定 | 後續文件處理 |
|---|---|---|
| 操作手冊：安裝、COM、監看與正式記錄分開 | 仍適用；安裝啟動腳本存在；app.py 的 connected 事件開啟已啟用力規；Controller 分離監看與 CSV | 保留，補現場接線／安裝圖片及最新 UI |
| 操作手冊：「實驗／裝置設定」單一入口 | 現行 app.py 分「實驗設定」「裝置設定」，另有「PID／PLL」「螺旋槳管理」 | 更新操作路徑，不讓新人尋找舊入口 |
| 操作手冊：記錄儀器歸零、校正公式 | 公式與人工硬體歸零記錄仍適用，但未說明 tare_force 的新軟體歸零與限制 | 補第 4 節條件、保存／載入方式、原量測與 raw count 的區別 |
| 操作手冊：等停機後記錄完成 | 預設等待仍適用；現行可在 poststop 提前停止記錄並留事件 | 補提前結束規則，不能把按鈕當作機械停穩判定 |
| 存檔規則：REAL／SIMULATION＋時間 | session_files.py 現行 REAL 省略模式／時間並以 _A…去重；SIMULATION 才保留模式時間 | 歷史原件保留；現行操作以第 6 節為準 |
| 存檔規則：自訂建議名 | 人工實驗 ID 建議可沿用，但選槳後 Controller 的 label_override 會覆蓋 run_name 對測次資料夾的作用 | 分清人工 ID、實驗設定 JSON 名與自動資料夾名；保留已知程式差異 |
| 模組責任／Class 圖 | 單一 Controller、SensorWorker、Motor、報告背景工作的架構仍適用；新增 propellers.py、pid_settings.py、pid_dialog.py 等未列入 | 補新模組、PidDialog 與 PID／歸零相關方法及資料流 |
| 架構文字：Motor 與 SimMotor 相同介面 | 基本 sample／ramp／start／stop 等共同介面仍成立；v0.3.22 Motor 另有 read_pid／write_pid，SimMotor 沒有 | 限定為共用馬達流程介面，不宣稱完整 API 等同；PID 僅實機 |
| State 圖：Recording 群組、主 phase | 主要 phase 仍一致，Recording 本來就是文件群組；停止逾時後進 poststop 仍成立 | 補 finish_poststop 提前結束、失聯／關閉及 force 獨立狀態；pid_unverified 是旗標，不應當作既有 phase |
| Sequence 圖：begin→建 JSON→取樣 | 主順序仍成立，但 Controller.begin 在建檔前可能讀取 PID，並檢查未確認寫入／槳葉方向 | 加 PID 已讀／未讀分支、拒絕分支及參數快照；單項寫入前讀、寫、後讀另補 sequence |
| Flow 圖：「不可開始→顯示原因並保留事件」 | app.py begin 可只顯示對話框；Controller.write 在未開 CSV 時直接 return，因此開始前拒絕不保證有持久化 CSV 事件 | 改為區分 UI／記憶體 log 與已開檔的 CSV 事件；不可承諾所有失敗皆落盤 |
| CSV／HTML 與原始資料 | 原始資料保留、非同步取樣、末段不是穩定判定仍適用；v0.3.21 後 HTML 與 CSV 方向語意不同 | 補方向係數與對照規則；不可拿反號後 HTML 直接與原 stages 同號比較 |
| 存檔規則：新分析另名、不覆寫 | 這是人工規範；report.generate_report 寫同名 data_report.html，summarize 寫同名衍生 CSV，重產可能替換舊衍生檔 | 分析前另存／複製，不能宣稱工具自動保留歷版；原始 CSV 不因此改寫 |
| 歷史 CW 標記 | archive_rules、D03、兩份會議稿稱早期 1050 為 CW；02_PROJECT_MEMORY 另記使用者後來確認一包舊資料皆反裝 CCW | 已以相同 CSV 雜湊確認早期 R001–R005 在 PP(2) 範圍內；衝突來源並存，後來反裝 CCW 說法僅套第 14 節列明的 11 組，不改舊檔或自動套新符號 |
| 會議稿：0.01 N／10–20 s | 文字確實寫 N，但仍是歷史整理，沒有窗口、起算點與正式簽核 | 可引用為歷史要求；不可直接用作已核准驗收門檻 |
| 會議稿：4000–5000 rpm、明早 demo | 是當時工作目標與提案；後續歷史另提 11000 rpm，現行軟體上限仍 7100 rpm | 保留時間背景；不把任何歷史目標當已允許或已驗收轉速 |

### 11.3 歷史決策接續

- D01「v0.3.11、不改程式」是當時版本範圍；當前基準已為 v0.3.22，本次依然只改交接狀態文件。
- D02 每輪獨立資料夾／HTML、補人工 metadata：仍適用，資料與模板不能互相取代。
- D03 三葉槳及 2600 rpm 對應葉通頻率 130 Hz 的計算背景可保留；CW 與後來反裝 CCW 說法的同資料映射已完成（第 14 節），仍缺實際方向照片；約 9 Hz 記錄不能證實共振。
- D04 拆裝與 A/B 歸零差異、D05 C/D 偏移延續：作歷史觀察保留，非本次重新證實。
- D06 各接頭鎖付分開規範、D07 一次改一項排查、D08 獨立轉速核對：仍是適用的實驗原則，尚無本次執行結果。
- D09 4000–5000 rpm 比較：歷史計畫，不能宣稱已完成或涵蓋後續全部需求。
- D10 表面／撓曲屬主觀觀察：仍適用，不自行推導材料缺陷或性能排名。
- D11 文件／UML／測試初稿已建立：本次已讀到並核對，後續補版本差異；不再列為從未產出。
- D12 Safety／V-model optional：保留，不自行升格為既定認證要求。

### 11.4 主管要求覆蓋與缺口

| 主管要求 | 已有文件／證據 | 尚有缺口與完成定義 |
|---|---|---|
| 使用者 README／manual | README、user_manual、發布包 README | 統一 v0.3.22 操作、圖示／接線、安裝環境與已知限制；新人實際照做的回饋 |
| 新人訓練 | onboarding 8 階段、必答題、帶教欄位 | 補新歸零／方向／PID、設定保存載入；填實際日期、證據與帶教簽核，不能用空模板代表受訓完成 |
| 開發者文件 | architecture 的責任表與主要流程 | 新模組、資料欄位／事件 schema、執行緒與錯誤回復細節；未見完整 API 參數、回傳、例外與合法呼叫狀態契約 |
| Class／State UML | architecture 內兩種 Mermaid 初稿 | 更新新增方法／旗標與力規狀態、例外分支；正式審查與版本同步 |
| Sequence／Flowchart | architecture 內兩種 Mermaid 初稿 | PID 單項讀寫驗證、歸零、STOP 插入、提前結束、連線／磁碟失敗的必要分支與持久化界線 |
| Unit Test | test_matrix T01–T17、現行 unittest 檔；前次 2 項 PID Mock 通過 | 未要求立即換框架；補新功能覆蓋、固定環境及版本結果；GTest 僅在需要 C/C++ 測試時評估 |
| 功能符合預期 | T14、change_record 的需求 ID 與驗收欄位 | 尚無完整需求→測試→實際結果追溯表；需主管確認 V1.0 通過條件 |
| 型別／隱含轉型、範圍 | T15／T16 候選、validate_plan、PID encode_value 及部分現行測試 | 逐欄輸入契約、上下界／越界／NaN／Inf／bool／空值系統化覆蓋；有驗證程式不等於覆蓋完整 |
| API 錯序／競態 | T17 候選、重複連線／停讀中啟動等既有測試 | 確認白板原意；每狀態合法命令表、PID／歸零／STOP／重連的交錯測試 |
| 實驗追溯與交接 | archive_rules、experiment_record、decisions、change_record | 已填測次與變更範例、共同存放位置／權限／保留期限、版本回復演練與責任人 |
| 結構精簡與物件生命週期 | architecture 重構候選、roadmap 小步重構流程 | 屬提案；不能宣稱已完成重構。依實際需求與測試風險決定拆分 |
| Safety／V-model optional | roadmap、D12 | 尚無專門文件；必要程度與格式待主管指定，不列為既定強制缺失 |
| V1.0 ready | roadmap 有候選驗收條件 | 新人、Windows、指定硬體、關鍵功能與限制簽核未完成；文件齊備不等於產品驗收 |
| 未來 skill | roadmap 有 5 步 AI 工作流程 | 尚未建立／安裝 skill；本包未見獨立可安裝 skill 或完整觸發規則；不能因此推論其他位置沒有交接 Prompt |

現行測試補充盤點（靜態檢查，不是本次執行結果）：
- T01–T13 引用的測試檔仍存在，核心主題仍可定位；T14–T17 本來就是部分覆蓋或候選，保留其未完成標記。
- v0.3.22 已增加 test_pid_settings.py 的 2 項測試，歷史矩陣未收錄。仍需規劃首次讀取不支援、expected 不符、讀寫逾時、斷線／重連、pid_unverified 對 begin 的阻擋、JSON 快照與 GUI 狀態等驗收。
- 既有 test_calibration 主要驗證兩點校正／換算，不等於完整 tare_force 驗收；未定位到直接覆蓋 1.5 s／0.5 s／3 筆／2 count 各門檻的專項測試。
- 未定位到直接測試四組 direction_factors、選槳 label_override 優先序、REAL 去時間與結果標記、finish_poststop 提前結束的專項案例；既有泛用命名／報告測試不能直接代表以上新版功能全部驗收。
- 上述是測試補缺清單，本次沒有新增測試、修改測試或重新執行全套測試。

### 11.5 盤點結論與後續順序

歷史文件狀態由「既有文件待讀取及核對」更新為：**12 份均已讀取，v0.3.22 靜態差異與主管要求缺口盤點完成；歷史文件維持初稿原貌，版本修訂與正式審查待後續任務。**

下一輪可依使用者指定，先更新操作手冊／新人訓練的直接操作差異，再補 UML／API／測試矩陣與需求追溯；每項沿用已有文件，不重建一套平行版本。實機驗證仍需現場資料與結果，文件盤點不改變 PID／PLL 尚待實機及 48 V 尚未修改／燒錄的狀態。

## 12. 48 V 邊界與仍待補資料

原先僅見於歷史記錄的 25 V 額定、30.0 V OV、4.0 V UV 與分壓係數，現已由補交工程確認（第 13 節）。**這份原始工程不是已完成 48 V 修改的證據；48 V 修改及燒錄仍未完成。** 附帶 ELF 不證明板上已使用該版本，也不證明它與目前工程逐項一致。

仍待補／待驗證：

1. 公司端最新進度、板號／硬體 revision、實際燒錄檔與紀錄、可核實的板端版本識別／flash 對照及可回復程序。已收到的工程與 ELF 不再列為缺件。
2. 50 V／30 A 是額定還是絕對上限的原始規格；電路圖、實裝分壓／ADC／功率級／電容／回生條件；48 V 工作範圍、正式 OV／UV 門檻與驗收條件。
3. 實際馬達型號／銘牌與電參數，確認是否真對應 RUM-3848Y_5K／7 pole pairs；力規、變送器 F7、力臂、校正負載、接線與電供規格。
4. R009、R013、R014 的旋向／裝法；早期 CW 與後來反裝 CCW 衝突的現場證據；每輪歸零、拆裝、鎖付及方向視角紀錄。已收到的 17 組原始資料不再列為未提供。
5. v0.3.22 實機 PID／PLL 讀取、停機單項寫入與讀回、失敗／逾時／重連、未確認寫入阻擋實驗的結果及 JSON 快照。先核對公司端是否已有結果，不重做已完成工作。
6. 約 6000 rpm 故障的完整 log、獨立電供限流／電壓／電流紀錄；漂移正式窗口、門檻與實驗控制條件。現有資料沒有獨立電供量測，不能補證 3 A 限流時序。
7. 第 11 節既有文件的新版修訂與審查、現場新人帶教／Windows GUI／DPI 證據、需求到驗收追溯；skill 尚未正式建立／安裝。

## 13. 補交韌體工程核對

### 13.1 來源、編譯產物與板上版本分界

- ZIP：RC100D_Rum3848yMotorTest.zip；SHA-256 `41603defaee534d3ad135fb1fd9e9a872a0a9d343dc35f5803a438472ed4675f`。解壓 1,646 個檔案、CRC 通過；相對工程根目錄為 `RC100D_Rum3848yMotorTest/`。
- **原始碼設定**：以下由 .ioc／.wbdef、產生的 headers、配置與協定實作核對；所查關鍵 .ioc／.wbdef 設定一致。設定名稱／註解不等於實際馬達或硬體額定。
- **既有產物**：`STM32CubeIDE/Debug/RC100D_Rum3848yMotorTest.elf`，2,119,048 bytes，SHA-256 `a607a0d37db82bba198c653c5011975a23c38521f9954220a378eda0f56cac9a`。已讀 ELF header：ELF32 little-endian ARM EABI5、hard-float、含 debug info，entry 0x080005e5。另有 .map（928,405 bytes）、.list（1,033,950 bytes）、68 個 .o 及建置清單；未見 .hex／.bin。map 可定位 PIDSpeed／PIDIq／PIDId／STO_PLL／VBUS／scale 等符號。
- **限制**：本次沒有重新編譯、反組譯驗證所有初值、重現建置或讀板。不能宣稱 ELF 與當前來源完全一致，也不能宣稱該 ELF 已燒錄。資料 JSON 明示 firmware_identity 未讀回。

### 13.2 MCU、馬達及速度設定

| 項目 | 原始工程確認 | 來源 |
|---|---|---|
| MCU | STM32G431CBU3，STM32G431C(6-8-B)Ux／STM32G431CBUx，UFQFPN48，CPU 170 MHz | .ioc MCU／clock 設定 |
| SDK | MCSDK 6.4.2；STM32Cube FW_G4 V1.6.2 | .ioc／.wbdef、隨附 SDK |
| 馬達設定 | RUM-3848Y_5K；description=5000R-5A；PMSM；7 pole pairs；Rs=0.1 Ω；Ls/Lq=20 µH；Ke=0.8 Vrms phase-phase/krpm | .wbdef／Inc/pmsm_motor_parameters.h |
| 電流設定 | NOMINAL_CURRENT_A=30 A、IQMAX_A=30 A、demagnetization=-30 A；與名稱中 5A 不同，不能視為銘牌額定已確認 | 馬達／drive headers |
| 回授 | STO_PLL 主速度估測，無輔助感測器；encoder PPR=400 等殘留設定不代表實際啟用 encoder | .ioc、drive_parameters.h、mc_config.c |
| 控制率 | PWM 30 kHz、FOC 每 PWM 一次、Speed loop 1 kHz | drive_parameters.h |
| 速度設定 | MAX_APPLICATION_SPEED_RPM／MOTOR_MAX_SPEED_RPM=12000 rpm、MIN=0、預設目標 2000 rpm | 馬達／drive headers |
| 速度單位 | SPEED_UNIT=10（0.1 Hz），U_RPM=60，內部速度單位對應 6 rpm；通訊速度值／ramp 以 rpm 交換 | mc_stm_types.h、sync_registers.c |
| 開迴路起動 | 5 段：10 ms/0 rpm/3 A；5000 ms/100 rpm/7.5 A；5000 ms/400 rpm/7.5 A；5000 ms/800 rpm/7.5 A；5000 ms/1500 rpm/7.5 A | drive_parameters.h、mc_config.c |
| Observer 切換參數 | 第 3 phase 起啟用估測檢查、最低 1200 rpm、連續 5 次、速度界線 14/16 與 18/16、transition 25 ms | drive_parameters.h |

韌體 12000 rpm、Python 7100 rpm、歷史實驗清單最高 5000 rpm 是不同層級，均不等於機械安全額定或全區間驗收。Python 固定先命令 1500 rpm 不會取代 MCU 的 Rev-up 設定。歷史其他馬達型號／KV 或 11000 rpm 目標不能自動套入此工程。

### 13.3 電壓保護與 VBUS 換算

| 項目 | 工程內容與解讀 |
|---|---|
| 額定／保護 | NOMINAL_BUS_VOLTAGE_V=25 V；OV_VOLTAGE_THRESHOLD_V=30.0 V；UD_VOLTAGE_THRESHOLD_V=4.0 V；OV／UV enabled |
| 分壓／ADC | VBUS_PARTITIONING_FACTOR=0.03194888178913738；ADC_REFERENCE_VOLTAGE=3.3 V；ADC2 channel 3／PA6，47.5 cycles |
| VBUS sensor | REAL_SENSOR；conversion factor=(uint16_t)(3.3/ratio)=103；不是浮點全精度電壓回報 |
| OV raw | `(uint16_t)(30.0*65535/(3.3/ratio))`；OV high／low 使用同一來源門檻 |
| UV raw | `(uint16_t)(4.0*65535/((uint16_t)(3.3/ratio)))`；分母先轉 uint16，與 OV 公式不同 |
| 回報 VBUS | `uint16_t((uint32_t)AvBusVoltage_d * ConversionFactor / 65536)`，以整數 V 經暫存器回報；不可誤套電流 SCALE |
| 保護路徑 | mc_tasks.c 透過 RVBS_CalcAvVbus 納入 fault 處理；.ioc 配置 TURN_OFF_PWM。設定存在不代表實際門檻／跳脫時序已量測 |

來源：Inc/power_stage_parameters.h、drive_parameters.h、parameters_conversion.h；Src/mc_config_common.c、mc_tasks.c；SDK bus_voltage_sensor.c。理論 ADC 全尺度約 103.29 V 只是分壓換算，不能推論板子耐壓或允許輸入。工程 metadata 的板級 50 V／30 A 也不能替代硬體規格驗證。

### 13.4 PI／Observer／PLL 及通訊對照

| 控制項 | 原始碼預設 | Python v0.3.22／wire 對照 |
|---|---|---|
| Speed PI | Kp=2810、Ki=622；divisor 128／16384；D 未啟用 | element 2／3；divisor 81／82，wire 指數 7／14 |
| Iq／Id PI | 兩者 Kp=2949、Ki=983；divisor 8192／16384；D 未啟用 | Iq 6／7，Id 10／11；header KD=100 不代表 D 生效 |
| Observer gains | GAIN1=-11264、GAIN2=21889；F1=8192、F2=16384 | element 13／14，signed int16 |
| Observer 命名差異 | SDK GetObserverGains／SetObserverGains 操作 hC2／hC4 | 外部 MC_REG_STOPLL_C1／C2 是上述兩個可調 gain，不能與內部物理公式 C1／C2 等同 |
| PLL | Kp=1490、Ki=35；KPDIV=16384、KIDIV=65535；mc_math.h 的 LOG2(65535) 特別回傳 16，配置使用該指數 | Kp element 18、Ki element 17；host 僅改 gains，不寫 PLL divisor；不可把 Speed divisor 規則直接套成 PLL 設定解讀 |
| Iq reference | element 37，raw int16 | 韌體資料項存在，host 面板僅讀；不能宣稱 host 提供 Torque Reference 寫入 |

通訊與縮放：

- USART3、PC10 TX／PC11 RX、1,843,200 baud、8N1，DMA1 channel 1／2。UART 初始化在 Src/main.c，沒有獨立 Src/usart.c，不是原始碼讀取失敗。
- ASPEP version 0、DATA_CRC=0（header CRC4 仍存在）、sync TX/RX 256 bytes；韌體另支援 async 2048 bytes，host 使用同步交易，不能宣稱 async 已驗收。
- 歷史／host 文件稱 MCP v2／ASPEP；隨附 SDK `mcp.h` 的 `MCP_VERSION` 巨集為 `0x1U`。保留實際巨集與外部名稱，不能改寫成「巨集為 2」或用協定名稱證明板上版本。
- register ID=`(element<<6)|(type<<3)|motor_id`，Motor ID 1；16-bit type 的 ID 為 `(element<<6)|0x11`。GET=0x11、SET=0x09、START=0x19、STOP=0x21、FAULT_ACK=0x39。
- host 常用回報 ID：status 0x49、faults 0x19、speed 0x59、speed ref 0x99、control mode 0x89、VBUS 0x591、temperature 0x5d1、power 0x1b59、Iq 0x8d1、Id 0x911、SCALE 0x129、ramp 0x1a9。命令與資料 ID 屬不同封包位置，數值重複不代表混用。
- VBUS uint16 V；temperature int16 °C；power float32；Iq／Id signed int16 raw。ramp payload 為 int32 rpm＋uint16 ms。
- SCALE_CONFIG payload 為 3 個 float32（12 bytes）：voltage=`25/(1.73205*32767)`，current=`3.3/(65536*0.044)`=0.0011444091796875 A/count，frequency=6。電壓 SCALE 不等於 VBUS 原始 ADC 換算。資料包已存的相符係數只支持換算一致性，不能認定來源／板上版本相同。
- PID 讀寫 ID、signed gain 與 Speed divisor 指數語意在所查來源中可對應 v0.3.22；**實際板上支援、寫入後回讀、停機條件與重連仍待實機驗證**，本次未執行任何寫入。

### 13.5 實際讀取範圍與限制

完整讀取／核對配置檔：工程 .ioc、.wbdef；Inc/pmsm_motor_parameters.h、drive_parameters.h、power_stage_parameters.h。另讀取並定位相關實作：Inc/parameters_conversion.h、register_interface.h、mcp_config.h；Src/mc_config.c、mc_config_common.c、mc_parameters.c、sync_registers.c、main.c、mc_tasks.c、mcp_config.c；Inc/mc_math.h、mc_stm_types.h 及 SDK 的 mcp.h、bus_voltage_sensor.c、sto_pll_speed_pos_fdbk.c、pid_regulator.c／相關宣告。附帶 ELF 以 header／雜湊檢查，map 以符號與建置內容檢查；不把 binary 當全文程式閱讀。

所有工程封裝檔均完成解壓 CRC 與原封裝逐位元回比；這不是宣稱 1,646 個 SDK／HAL／IDE 檔案已逐行語意審查。所需設定與資料讀取未遇無法讀取檔案；未取得的板上 dump／實際燒錄紀錄屬缺資料，而非讀檔錯誤。

## 14. 歷史實驗最後盤點

完整交付：**EXPERIMENT_INDEX.md** 為可讀索引；**EXPERIMENT_INDEX.json** 保存全部 49 筆來源、17 組唯一資料、完整 metadata／事件及五檔雜湊。索引 R／O／Z 編號只是本次追溯 ID，不重命名原件。

| 項目 | 已核對結果 |
|---|---|
| 範圍 | 8 個實驗 ZIP、49 個測次資料夾、245 個輸出檔；全部五檔可讀，無缺檔 |
| 重複 | 17 組唯一 data.csv；各重複群組的 JSON／summary／stages／HTML 也完全相同；PP(1) 與 PP(2) ZIP 本體相同 |
| 版本 | v0.3.11：12 組；v0.3.17：2 組；v0.3.20：3 組；沒有 v0.3.22 實機測次 |
| 結束 | 16 組 sequence_complete、R009 為 operator_stop；未見錯誤結束或已記錄非零 motor fault。不能等同量測驗收 |
| 舊反裝 CCW 範圍 | 02_PROJECT_MEMORY 第九節明指 PP(2) 的 11 組；映射為 R001–R008、R010–R012。相同 CSV 副本可追溯該歷史聲明，非 JSON 本身含有此設定 |
| 排除延伸 | R009 只有原 PP 包，不屬上述 11 組；R013／R014 v0.3.17 缺方向／裝法；三者保持未知。R015／R016 JSON 為 CW 正裝，R017 為 CCW 正裝 |
| 歷史文字衝突 | archive_rules、D03、會議準備稿早期 CW，與後來反裝 CCW 說法有衝突；相同 CSV 已確認 R001–R005 確在後者範圍。保留兩者來源與證據層級，不改原件／自動反號 |
| 名稱與計畫 | R010 原 PP 包檔名只到 3000，JSON／完成事件到 5000 共 8 點；R012 名稱僅前 4 點、實際計畫為 7 點；完整差異與路徑已列索引 |
| 名稱與結果 | R009 檔名未標 Abort，CSV 明示 operator_stop；不得用普通檔名當作成功 |
| 量測限制 | 全部 psu_enabled=false；只有 motor／force 量測；無 direction_factors／pid_board_readback；firmware_identity 未讀回 |
| 通道設定 | 全部 CH1 0.01 N/count、CH2 0.001 N·m/count、軟體 zero1/zero2=0；不能由零設定推論硬體沒有歸零或漂移 |

本次完成的工具檢查：9 個新 ZIP CRC、全部解壓檔案與 ZIP 原 bytes 再比對（1,891 檔全數一致）、49 JSON／147 CSV 解析、49 HTML 完整文字讀取、事件與設定清單比對、重複雜湊分析、韌體靜態核對及 ELF header 檢查。**未修改歷史文件、程式、韌體或量測；未編譯、燒錄、重產報告、執行硬體或新一輪應用程式測試。**

成功讀取與仍缺資料已分列第 1／12／13 節及實驗索引；本批實際讀取失敗為 0。盤點並未證實歷史漂移根因、48 V 可用性或 PID／PLL 實機驗收。

交接資料盤點完成。後續建議先由使用者指定處理方向衝突／缺失現場紀錄、v0.3.22 驗證或文件更新；本次不自動進入上述工作，等待下一項任務。


## 15. 2026-11-05 PID／PLL 介面改版 v0.3.23

使用者確認採用 Motor Pilot 相近的分頁／分組設計。交付 Robi_Integrated_Automation_v0.3.23.zip，舊 v0.3.22 保留作回復；不是實機驗收通過版。

- 新版使用 Currents / Speed 與 Observer / PLL 雙分頁，Speed／Iq／Id 分組；各列板端讀值、待寫入值、單項寫入與狀態分離。
- ＋／− 只改待寫值；Speed divisor 下拉；Torque Reference 維持 raw 唯讀；不顯示沒有對應功能的 CORDIC。
- 沿用安全寫入與讀回流程；補確認視窗後快照檢查。未送出草稿保留，快照因失敗／停止／斷線失效則清除並要求重新讀取。
- 修改 pid_dialog.py；app.py／controller.py 僅版本更新；新增 test_pid_dialog.py 與發布說明，更新 README／CHANGELOG／VALIDATION 入口。沒有變更通訊協定、量測單位、方向換算或韌體。
- 工具測試：既有 68 項中 67 通過、1 GUI 跳過；新增 6 項 UI 狀態測試通過；合計 73 通過、1 跳過。Python AST 全部通過。測試涵蓋單項送出、負數／邊界、取消與條件拒絕、確認期間快照改變、失敗清除及草稿保留。
- 限制：本環境無 DISPLAY，未實際渲染新版 Tk 視窗；Windows 字型、DPI、裁切與按鍵驗收待做。未開實體埠，PID／PLL 實機驗證仍未完成；48 V 韌體修改／編譯／燒錄仍未完成。
- 本次沒有新增實驗測次；EXPERIMENT_INDEX 保持 17 組唯一資料、49 筆來源，舊版本測次標籤不變。
- 後續待使用者提供 Windows 新版畫面／操作結果再記錄驗收；不自動進入硬體測試。


## 16. 2026-11-05 v0.3.24 PID／PLL 交易狀態修正（歷史紀錄）

> 2026-11-05 v0.3.25 勘誤：下列 v0.3.24 的「開始實驗前 PID pending 防護」描述範圍過大。原始碼僅在 start_force 檢查，力規停用時可開始，啟用時也已先建檔。本次以真實 Controller＋替代設備重現，於 v0.3.25 的 App／Controller.begin 修正。下文保留原發布紀錄；v0.3.24 ZIP 未覆寫。詳 RELEASE_v0.3.25.md。

使用者授權在 v0.3.23 上最小範圍修正，不重排版面、不改協定／量測／實驗階段／韌體、不操作硬體。v0.3.23 原始 ZIP 保留。

原缺陷已先用離線可控制順序重現：STOP 後舊讀值回填、重建 presenter 遺失 pending、舊回覆解除新 pending、寫入後 STOP 清除 unverified、成功列不保留已驗證。原版重現 11 項＝6 通過＋5 預期失敗，完整輸出收錄新版 validation/reproduction_v023.txt。重建 presenter 不等於真實 GUI 關窗驗證。

新增修改：pid_transactions.py 由 Controller 擁有跨視窗狀態，以 id＋generation 配對每筆請求／進度／完成／失敗。STOP、斷線、連線世代改變使舊請求失效；舊回覆保留稽核日誌，但不能建立快照或清除新交易。寫入送出點後一律保守保留 unverified，取消 UI 不等於取消板端寫入；新有效讀取才可重新確認。App.poll_once 在視窗關閉時仍處理交易；PidDialog 只呈現共享狀態及草稿。

列狀態分草稿（未修改／已修改／輸入無效）與交易（寫入中／讀回驗證中／已驗證／未確認／失敗）；結果不被 refresh 洗掉。成功與失敗均含參數、舊值→新值及原因；日誌含請求 ID、世代、可能已送出標記與取得的讀回值。沿用既有日誌管道，沒有新增跨重啟獨立 log 檔服務。

修改檔：app.py、controller.py、pid_dialog.py；新增 pid_transactions.py；版本字串為 0.3.24。protocol.py、pid_settings.py、單位／校正／報告與 theme 均位元組一致，PID _styles／_group 不變。開始實驗前增加 PID pending 拒絕條件，僅作交易安全防護，實驗階段流程不變。

驗證結果：最終 `python -m unittest discover -v` 共 **95 項，91 通過、0 失敗、4 跳過**。4 項＝原主畫面 GUI 1 項＋新增真實 PidDialog GUI 3 項（無 DISPLAY）。headless presenter 測試實際執行 Tcl StringVar／trace，但 widgets mocked；不得稱 GUI 驗證。新增 App 測試使用 Event 控制 I/O 等待，證明 STOP 不需等待該交易完成、晚到回覆不能清 unverified；不依賴任意 sleep。各輪中間測試數與最終數不累加。所有 Python AST 通過。

包內 RELEASE_v0.3.24.md 記載逐問題重現、根因、修改位置與完整驗收範圍；validation/final_suite.txt 保留逐項結果。Windows 排版／DPI、板端讀寫仍未實測；PID／PLL 實機驗證、48 V 韌體修改／編譯／燒錄均仍未完成。實驗索引仍為 17 組唯一測次，未新增或覆寫原始量測。

回復：關閉 v0.3.24 後啟動保留的 v0.3.23；軟體回復不會回滾已寫入板端的參數，須重新讀取確認。後續等待使用者提供實測結果或下一項需求。


## 17. 2026-11-05 v0.3.25 最小範圍修正（歷史基準）

## 修正與重現證據

| 原有缺陷 | v0.3.24 實際觀察／根因 | v0.3.25 修改位置與行為 |
|---|---|---|
| PID 與實驗啟動互斥不完整 | 真實 Controller 執行緒的 PID 成功事件已入 events、App 尚未接受；力規關閉時仍建資料夾並呼叫替代馬達 start；力規開啟時先 session_begin 才在 start_force 報錯。防護錯放在力規分支 | controller.py 的 begin／start_block_reason 在任何設備 I/O、建檔前拒絕 pending、unverified、blocked；同一 pid.lock 原子保留 experiment 執行資格，與 request_pid 互斥。鎖不涵蓋設備 I/O。app.py 的 begin 在確認前後檢查並核對世代，開始按鈕使用同一判斷。移除 start_force 中錯置的實驗防護，力規監看與實驗入口責任分開 |
| disconnect→STOP 永久 blocked | 以 Event 卡住 sample，再排 disconnect、提出 STOP；STOP 丟掉 disconnect 命令後 motor 仍存在、blocked=True、commands 為空 | controller.py 的 submit 保存獨立 disconnect_requested 意圖；clear_stopped_commands 清佇列不清意圖；service_disconnect 在停止及必要 poststop／紀錄處理後完成斷線。完成斷線才解除 blocked，保留 unverified。被 STOP 取消的 connect／begin／force_tare 等命令產生 command_error，讓 App 清除預先顯示的等待狀態 |
| 操作提示被 refresh 覆寫 | Speed Kp=32767 按＋產生範圍錯誤，下次 refresh 變回已讀取板端。操作提示在視窗，交易訊息在共享狀態 | pid_transactions.py 加入共享 hint 與優先序；pid_dialog.py 的 step／read／write 改走同一來源。錯誤保留至有效編輯或操作；STOP、失敗、未確認、正在進行的交易優先，低優先提示不得覆蓋。每列已驗證結果及其他草稿規則沿用 |

上述為 v0.3.24 既有缺陷；本次新增的是互斥資格、耐 STOP 的斷線意圖及提示優先序，並非宣稱原版已具備這些防護。前次發布文件「開始前已完整阻擋 PID pending」的表述不成立：實際只在 start_force 分支檢查。原 v0.3.24 ZIP 不覆寫；本包的歷史發布說明及交接文件加註勘誤。

## 狀態責任與優先序

| 狀態 | 定義／設定者 | 解除時機 |
|---|---|---|
| pending（active 非空） | Controller.request_pid 透過共享 PidTransactions 保留交易。包含讀／寫進行中及成功事件已排隊但 App 尚未接受 | 匹配 ID／generation 的終態被 App 接受，或 STOP／斷線使交易失效；舊回覆不解除新交易 |
| blocked | Controller 管理的連線轉換中狀態，不代表一般斷線，也不是寫入未確認 | 連線成功／失敗或斷線實際完成後更新；若已有待處理斷線意圖，連線完成仍維持封鎖。斷線後 motor=None，另由連線檢查拒絕操作 |
| unverified | 寫入送出前保守設定；STOP／斷線無法推論板端未寫入 | 只有當前有效讀取／寫後讀回成功且被接受，才解除。清佇列、重連、停止、丟棄晚到回覆均不解除 |
| experiment | Controller.begin 在同一 pid.lock 下取得的實驗資格，包含啟動準備與記錄期間 | 建立失敗且無開啟紀錄、finish 關檔、例外強制關檔或完成斷線；阻止此期間再取得 PID 資格 |
| disconnect_requested | submit('disconnect') 即保存，獨立於 commands | 停止與必要紀錄處理後，斷線完成才清除。STOP 優先停機，斷線意圖仍必須執行 |

操作提示與交易狀態使用不同欄位，但由 view 統一決定顯示：STOP／交易失敗（important）、unverified、pending 的交易訊息優先於 hint。有效編輯或有效操作清除舊 hint；無效編輯不清除。新的有效交易可取代先前終態訊息，不修改各列的結果保留規則。關閉視窗不影響上述共享狀態。

## 測試結果（實際執行）

| 執行 | 總數 | 通過 | 失敗／錯誤 | 跳過 | 證據 |
|---|---:|---:|---:|---:|---|
| 同一重現腳本對 v0.3.24 | 4 | 0 | 4 | 0 | validation/reproduction_v024.txt |
| 同一重現腳本對 v0.3.25 | 4 | 4 | 0 | 0 | validation/reproduction_v025.txt |
| 最終完整 unittest discover -v | 107 | 103 | 0 | 4 | validation/final_suite.txt；32.669 秒 |

新增 test_pid_interlocks.py 共 12 個測試方法，多個 subTest 覆蓋力規開／關、讀／寫等待、成功事件排隊未接受、直接 begin 在 I/O／建檔前拒絕、App 確認前後狀態變更、互斥資格、disconnect／STOP 兩種順序、重複 STOP、poststop 後斷線、已送出寫入未確認、取消命令回報、提示刷新及有效編輯。真實 Controller.run／commands／events 使用替代馬達與 Event 控制順序；新競態測試不使用任意 sleep。清理會停止並 join Controller、關閉紀錄並等待報告工作結束，不開實體埠。

test_pid_transactions.py 的一項舊測試更新為在 request_pid 入口即拒絕 SIMULATION 的新行為；原單項寫入、expected 舊值、安全條件、讀回驗證、晚到回覆、重開 presenter 及草稿測試繼續通過。中間完整一輪為 106 項＝101 通過、1 錯誤、4 跳過：錯誤是舊測試仍期待較晚拒絕 SIMULATION，已更新後重跑為上表 107 項。兩次沒有產生 unittest 結尾統計的中間輸出不列為完整執行或通過證據。

4 項跳過為主畫面真實 GUI 1 項、真正建立 PidDialog 的 GUI 3 項；原因為本環境無 DISPLAY。Tcl StringVar／替代 presenter 測試不算真實 Tk 視窗驗證。Windows GUI／DPI、PID／PLL 板端讀寫與實機驗證、48 V 韌體修改／編譯／燒錄均未完成。

## 範圍核對與回復

- 執行程式只修改 app.py、controller.py、pid_dialog.py、pid_transactions.py；版本字串及量測 metadata 版本為 0.3.25。
- protocol.py、pid_settings.py、units.py、calibration.py、config.py、sensors.py、devices.py、report.py、summarize.py、theme.py、session_files.py 與 v0.3.24 位元組一致。
- Controller.advance／next_stage／halt／enter_post／pid_command 及 PidDialog.__init__／_styles／_group 的 AST 一致。未重排視窗，未改通訊協定、單位換算、實驗階段或韌體。
- ＋／−仍只改草稿、一次一參數、實機／無故障 IDLE／0 rpm／未記錄檢查、expected 舊值及確認後重查、寫後讀回、Observer 有號數／divisor 編碼與合法值、Torque Reference raw 唯讀均保留。未自動寫 Flash、回滾或調參。
- validation/source_manifest.json 記錄 Python 雜湊與異動清單；附帶重現腳本可用相應來源目錄作 PYTHONPATH 重跑。舊驗證檔加 v024_ 前綴或保留原歷史命名，勿與本版結果混讀。
- 回復時使用原 Robi_Integrated_Automation_v0.3.24.zip 於獨立目錄；本次未讀寫原始量測。不建議在尚有背景工作／開啟紀錄時切換程式。

離線測試驗證的是軟體狀態與控制流程，不是硬體驗收。


## 18. 2026-11-06 v0.3.26 部分採納及驗證（目前基準）

## 相對正式 .25 的最小修改

| 位置 | 修改及邊界 |
|---|---|
| pid_transactions.py：reserve | 保持忙碌檢查先行；確認 update 結構、已知 key、expected 為整數、新值範圍／合法 divisor／唯讀限制，並先完成描述，才變更 sequence、active、提示與列狀態。非法輸入統一 ValueError，不留下 pending、不破壞既有交易。接受 list 後轉成 tuple，避免呼叫者後續修改交易內容。沒有修改 encode_value 或通訊編碼 |
| pid_transactions.py／controller.py | reserve_experiment 與 PID reserve 使用同一 RLock；Controller 在自己的連線／STOP 檢查後、仍持有同一鎖時取得資格。release_experiment 只清 experiment，完全不清 unverified；建立失敗、finish、斷線及強制關檔的原有釋放位置不變。不是 token 或完整所有權管理 |
| pid_transactions.py／pid_dialog.py | _message_is_protected 集中重要訊息判斷；available 同一次判斷只取得一次 view。accept／invalidate 的成功、失敗、草稿、列結果及 unverified 規則不變；未引入隱藏解除 unverified 的數值 helper |
| controller.py：_check_pid_write | 僅抽出編碼、無故障 IDLE／0 rpm、板端 expected 舊值檢查。主要流程仍依序顯示有效性檢查、前置檢查、標記可能送出、寫入、讀回核對、終態及稽核發布。未採納 _publish_pid_result。狀態鎖不涵蓋設備 I/O |
| pid_dialog.py：_styles | 選取頁為白底、深色粗體、底部色線；未選取頁為淺灰底、灰字。使用同尺寸 tab surface 與相同 padding，移除原未選取凸起外框；圖像留在 root，避免關窗後樣式引用失效。保留兩頁位置、名稱、內容與切換邏輯，未調整其他區域布局 |
| test_v03.py | 原摘要檔斷言改為等待該測次 data.csv 路徑的 finished 事件。等待有整體期限與明確逾時失敗，不加 sleep，不修改正式 finish 語意。finished 表示同步摘要流程已走完；非同步 data_report.html 仍由 report_ready／report_error 表示，不混為同一完成事件 |
| test_pid_refinements.py | 新增 8 項測試方法，含多個輸入 subTest、既有交易保護、競爭資格、RuntimeError 注入檢測、釋放不解除未確認、完成事件路徑及逾時、available 單次快照。競爭以 Barrier 同步，Queue 收齊兩個結果；非預期例外回主測試失敗，join 有限等待並檢查存活狀態；確認一方成功、一方因明確互斥原因遭拒 |
| test_pid_transactions.py／test_pid_gui.py | 既有安全測試改為確認非法 divisor／唯讀操作在入口直接拒絕且無 I/O。新增真實 PidDialog 分頁樣式／初始頁／切換內容／關窗重開測試，無 display 時明確跳過 |
| app.py／controller.py／文件 | 視窗與 metadata 版本更新為 0.3.26；CHANGELOG、VALIDATION、README、HANDOVER 更新目前摘要並保留歷史 |

## 測試歷程：保留首次失敗

1. **修改前紅燈測試**：在 .26 工作副本仍與正式 .25 執行程式相同時，先執行新增的前 6 個測試方法。1 方法通過，其餘 5 方法不通過；unittest 計入子案例後為 `failures=9, errors=9`。包含尚無 reserve_experiment API 的預期錯誤，以及缺少輸入原子驗證／list 隔離；不能把這 18 筆輸出稱為 18 個現場缺陷。原始輸出：validation/v026/before.txt。
2. **核心修改後目標測試**：先 6 項全過，補齊事件同步與單次快照測試後，8 項全過。原始輸出 targeted.txt、targeted_final.txt。
3. **第一次完整回歸**：116 個方法；110 通過、1 方法內 2 個子案例錯誤、5 GUI 跳過。兩個錯誤均在 test_safety_expected_readback_and_readonly：舊測試期待背景回覆拒絕，但新入口已直接拒絕唯讀參數及非法 divisor。這是本次驗證時機前移造成的測試期待不一致，已更新為 assertRaises 並增加無 sample／read／write／排隊的斷言；不是忽略例外。原始輸出 full_round1.txt。
4. **最終完整回歸**：`python3 -m unittest discover -s Robi_Integrated_Automation_v0.3.26 -v`；**116 項，111 通過、0 失敗／錯誤、5 跳過，32.646 秒**。原始輸出 full_final.txt。
5. **另行測試驗證用注入**：將 reserve_experiment 注入 RuntimeError，直接執行競爭測試，unittest 得到 **1 項刻意失敗、0 錯誤、0 跳過**，主測試訊息包含工作名稱與 RuntimeError。外層檢查確認此失敗符合預期；不計為正常回歸故障，也不冒稱競爭正常通過。原始輸出 injected_failure.txt。正常回歸另有一項 test-of-test 斷言上述注入必須被抓出。

本次涵蓋：非法輸入後恢復、既有交易不受損、資格競爭、建立失敗釋放、寫入後 STOP、disconnect／STOP 交錯、unverified 保留、舊回覆拒收、草稿及提示保留。沿用的 test_pid_interlocks 仍使用真實 Controller.run／commands／events 與替代設備；沒有開啟實體埠。新競爭測試所有工作執行緒有限等待並 join；未新增任意 sleep。

## GUI 與實機限制

5 項跳過為：主畫面 GUI 1 項、PidDialog GUI 4 項（含本次新增分頁樣式測試），環境無 DISPLAY，也未找到 Xvfb。已加入的 GUI 測試會檢查初始 Currents / Speed、切換至 Observer / PLL 再切回、實際顯示內容、選取色彩／粗體／底線圖像、相同請求高度及關窗重開；**本環境沒有執行成功，不能宣稱視覺驗收完成**。Tcl StringVar／mock presenter 通過不代表真正 Tk 視窗通過。

Windows GUI／DPI（包含分頁實際選取視覺）、PID／PLL 實機驗證，以及 48 V 韌體修改／編譯／燒錄仍未完成。需在 Windows 實際開啟初始頁、往返切換、關窗重開，確認樣式與內容一致及不同 DPI 無裁切；硬體驗收另行安排。

## 非範圍差異核對

- protocol.py、pid_settings.py、units.py、calibration.py、config.py、sensors.py、devices.py、report.py、summarize.py、theme.py、session_files.py 與正式 .25 位元組一致。其餘未列為修改的執行模組與設定／啟動檔亦維持原樣。
- Controller.advance／next_stage／halt／enter_post／submit／service_disconnect／clear_stopped_commands AST 相同；沒有變更實驗階段或 STOP／斷線語意。
- PidDialog.__init__／_group／_draft_changed／result／refresh／write AST 相同；只修改分頁樣式與 available 的快照使用，不改內容、位置或切換邏輯。
- PidTransactions.accept／invalidate AST 相同；unverified 的解除位置、列結果及草稿規則未改。
- 全部 Python 通過語法解析。原正式 .25 ZIP 與檔案逐一核對無修改；測試只使用暫存測次，未覆寫原始量測。
- from_v025.patch 是相對正式 .25 的根目錄 Python／Markdown 完整文字差異（含新增測試與文件）；validation/source_manifest.json 記錄異動清單與 Python SHA-256。歷史驗證資料保留歷史版本標記，勿以舊結果作本版驗收。

## 後續基準

目前正式交付基準為 .26，原 .25 ZIP 保留供回復；review-A 沒有升格為正式版。尚未建立新的硬體驗證結論。離線測試全過不等於硬體驗收完成。


## 19. v0.3.27 螺旋槳建檔


以正式 v0.3.26 為基準，僅調整螺旋槳建檔功能；原 .26 ZIP 保留供回復。

## 操作

- 自動排序：尺寸代碼 → 葉片數 → 材質 → 樣品編號 → CW／CCW。數字自然排序（02 在 10 前），同規格同編號的 CW 在 CCW 前；管理清單與主頁下拉選單一致。不更改既有名稱或編號。
- 單擊任意資料列帶入欄位，修改後按「另存新檔」建立新項目，保留原項目。相同名稱（忽略大小寫）拒絕新增；需更改至少一個命名欄位。儲存仍沿用既有流程，包括舊資料補登旋向；另存新檔不會刪除待補登旋向的舊資料。
- 預覽名稱右側「複製名稱」將目前完整有效的名稱複製到剪貼簿，可貼入 Excel。未填完整時顯示錯誤，不複製提示文字。例：1050_3-Blade_Black_No00_CCW。
- 沒有 Pair 功能，也不自動建立另一旋向；要複製 CW 成 CCW，可選取、改旋向、另存新檔。樣品編號可維持 00。

## 修改及保留範圍

app.py：排序、選列事件、另存新檔與複製按鈕及版本；propellers.py：純排序函式；controller.py：僅輸出 metadata 版本由 .26 改 .27。
未修改 PID、設備通訊、量測換算、方向規則、實驗階段或輸出結構。未操作硬體／韌體，未接觸使用者既有量測及現場 propellers.json。使用者螺旋槳資料仍由原工作目錄讀取，截圖中的資料未另行重建。

## 實際驗證

- 第一輪完整回歸：118 項，113 通過、0 失敗／錯誤、5 GUI 跳過。
- 加入真正建立 Tk 螺旋槳視窗的測試後，最終完整回歸：119 項，113 通過、0 失敗／錯誤、6 GUI 跳過。
- 新增兩項排序測試已執行：數字順序、旋向相鄰、混合文字尺寸、舊項目旋向空值及輸入不變。
- 新增真實 GUI 測試涵蓋選列帶入、僅 CW/CCW、複製名稱、另存保留原件、重名拒絕；本環境無 DISPLAY，該項與其餘五項 GUI 測試皆跳過。未將靜態檢查或替代物件當作 GUI 驗收。
- 所有 Python 檔通過 AST 語法解析；實際檔案差異見 validation/v027/file_diff.txt。完整兩輪 log 保留，沒有失敗後隱藏重跑紀錄。

## 待現場驗收

Windows GUI／DPI、選列及按鈕布局、剪貼簿貼入 Excel、另存及舊資料補登流程需實際操作驗收；PID／PLL 實機仍未完成。本次暫停 48 V 韌體工作，未修改、編譯、燒錄；公司端最新實際進度需以提供的工程及燒錄紀錄另行核對，不能由此離線測試視為完成。
