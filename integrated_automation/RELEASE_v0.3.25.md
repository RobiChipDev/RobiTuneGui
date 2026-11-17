# Robi v0.3.25 發布說明

日期：2026-11-05（Asia/Taipei）。基準：實際讀取的 v0.3.24 原始碼及 HANDOVER_STATUS.md。此版完成 Python 修改、離線重現與測試；未連接硬體。保留原 v0.3.24 ZIP 作為回復版本。

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
