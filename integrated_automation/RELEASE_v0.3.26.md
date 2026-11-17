# Robi v0.3.26 發布說明與驗證紀錄

日期：2026-11-06（Asia/Taipei）。基準是正式 Robi v0.3.25；review-A 僅作部分設計參考，未整包替換。正式 .25 原始碼與 ZIP 保留不動。本次未操作硬體，未修改／編譯／燒錄韌體。

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
