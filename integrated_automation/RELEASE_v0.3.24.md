> 2026-11-05 v0.3.25 勘誤：下列 v0.3.24 的「開始實驗前 PID pending 防護」描述範圍過大。原始碼僅在 start_force 檢查，力規停用時可開始，啟用時也已先建檔。本次以真實 Controller＋替代設備重現，於 v0.3.25 的 App／Controller.begin 修正。下文保留原發布紀錄；v0.3.24 ZIP 未覆寫。詳 RELEASE_v0.3.25.md。

# Robi v0.3.24 — PID／PLL 交易狀態修正

日期：2026-11-05（Asia/Taipei）。基於 v0.3.23；只修正 PID 交易生命週期及狀態呈現，不重排主畫面／PID 視窗，不變更 wire protocol、單位換算、實驗階段或韌體。不操作硬體。

## 已重現的原版缺陷與根因

在 v0.3.23 上先執行 validation/reproduce_v023.py，以 Mock 回覆與直接控制呼叫順序重現，不用任意 sleep 製造時序。此重現執行共 11 項：6 個原有測試通過、5 個「應安全」斷言失敗；這 5 個預期失敗是原版缺陷證據，不是新版回歸失敗。

| 原版缺陷 | 重現與證據 | 根因 | 新版修改 |
|---|---|---|---|
| STOP 後晚到讀值恢復快照 | read → result({}, STOP) → 舊 result(values)，值重新出現；另在 App poll 路徑測試 | pid_values 沒有請求識別；result 無條件回填 | 每筆請求／回覆含遞增 id 與 generation；STOP 先失效共享狀態，App 只接受同一有效交易 |
| 重開視窗可再送交易 | 第一個 presenter pending=True，新的 presenter 可操作；這是 headless 物件重建重現，非視窗實測 | pending/write_key 隸屬 PidDialog | Controller 持有 PidTransactions，跨視窗保存 active／快照／草稿；關視窗不取消交易 |
| 舊回覆提前解除新 pending | 舊請求失效後啟動新請求，舊 result 清 pending | 無交易配對 | active id＋世代不符直接忽略，連失敗及進度回覆也不能改新狀態 |
| 寫入後 STOP 仍清 pid_unverified | write_pid mock 設 STOP，舊程式仍讀回、清旗標 | pid_command 只在寫入前檢查 STOP，結尾無條件清旗標 | 寫入前標記 may-have-been-sent／unverified；中斷後保留；僅目前有效成功回覆能解除 |
| 成功列未顯示已驗證 | 成功回覆後 refresh 仍只有「與板端相同」 | _draft_changed 只推算草稿差異 | 交易列狀態另存；refresh 不清除，編輯該列才清掉舊結果 |

原版重現輸出完整保存在 validation/reproduction_v023.txt。真實視窗銷毀／重開案例已新增 GUI 測試，但本環境未執行成功，不能把 presenter 重建當成 GUI 驗收。

## 修改範圍與交易規則

- 新增 pid_transactions.py：Controller 所有的共享狀態，RLock 保護短時間狀態變更；不持鎖等待硬體 I/O。
- controller.py：request_pid 統一配置請求 ID；pid_command 發帶識別的 verifying／success／error 回覆；STOP、disconnect 提交／完成、連線建立及通訊失敗使世代失效。停止清理佇列與清 stop_event 在同一短鎖區段，避免新 PID 請求被靜默丟棄後永遠 pending。
- app.py：stop_all 立即失效；poll_once 先配對再呈現；即使 PID 視窗關閉，完成事件仍會被處理。update_pid_dialog 只讓視窗讀取共享狀態，不接受無識別舊回覆。
- pid_dialog.py：視窗只顯示共享 pending／快照／交易結果；StringVar 編輯同步草稿。確認視窗結束後重查可操作條件、expected 舊值及 generation，拒絕跨世代確認。
- 一筆 PID 尚未完成時不得再送另一筆，也阻擋開始新實驗。這是 PID 交易安全門檻，沒有改變實驗各階段、時間或測量流程。
- 取消前尚未到送出點：不再寫板；一旦通過送出點：保守記為「可能已送出」。取消 UI 交易不等於撤銷板端寫入，不回滾、不宣稱取消成功。
- STOP 後已送出的寫入即使晚到讀回值相符，舊回覆仍不能解除未確認；必須新發起有效讀取。斷線／重連不自行解除未確認。
- Controller 的 pid_unverified／pid_snapshot 讀取共享狀態；只有配對的成功回覆會建立快照／解除未確認。在 App 尚未處理回覆前仍維持 pending，避免驗證結果尚未呈現便啟動實驗。
- 正常成功保留其他列未送出的草稿；快照失效／交易失敗清除草稿並要求重新讀取；關閉／重開視窗仍保留未失效的草稿。

## 列狀態與追溯

草稿：未讀取／未修改／已修改／輸入無效。交易：寫入中 → 讀回驗證中 → 已驗證，或未確認／失敗／已取消。沿用原欄位，沒有新增版面區域。

每筆成功／失敗主訊息含參數名稱、舊值→新值與原因；日誌含請求 ID、世代、結果、write_may_have_been_sent 及 observed_values（若取得）。失效回覆仍留日誌，明示忽略；不能以其更新 UI 或解除旗標。沿用既有 App 日誌管道，未新增跨重啟的獨立日誌檔服務。

既有保護維持：＋／− 只改草稿、單筆單參數、實機／無故障 IDLE／0 rpm／未記錄、expected 比對、寫入後讀回、有號 Observer、Speed divisor 編碼及限制、raw 唯讀 Torque Reference；不寫 Flash、不自動回滾或調參。

## 測試與結果

| 執行 | 通過 | 失敗 | 跳過 | 說明 |
|---|---:|---:|---:|---|
| 原 v0.3.23 重現 | 6 | 5 | 0 | 5 個原版缺陷斷言刻意要求安全行為而失敗 |
| 首輪 PID 專項 | 22 | 0 | 3 | 新交易／presenter／原協定測試；真實 PID GUI 無顯示而跳過 |
| 首輪全套 | 87 | 0 | 4 | 當時尚未納入後續 4 項 App 測試 |
| App 專項 | 4 | 0 | 0 | poll_once、stop_all、關閉視窗、Event 控制寫入等待點 |
| **最終全套** | **91** | **0** | **4** | **95 項；25.779 s；以 validation/final_suite.txt 為準** |

各輪有重疊，不將通過數相加當成不同案例。新增時序測試以 Mock callback／threading.Event 控制進度；Event timeout 僅防止測試死鎖，沒有任意 sleep。既有其他測試保留原方法。

- test_pid_transactions.py：STOP 途中／完成已排隊、寫入送出後取消、舊回覆干擾新請求、斷線重連、單筆限制、階段結果、失敗／逾時解鎖、expected／安全條件／唯讀／divisor、未確認阻擋實驗。
- test_pid_app.py：真正呼叫 App.stop_all／poll_once，呈現元件 mock；包括 I/O 等待期間 STOP 可立即失效且晚到結果不能清 unverified。
- test_pid_dialog.py：Tcl StringVar 與 trace 真實執行，但其他 widgets mocked；驗證草稿、狀態與重建 presenter，不稱為真實 GUI 測試。
- test_pid_gui.py：真正 tk.Tk＋PidDialog；涵蓋兩分頁、輸入、StringVar 事件、按鈕、raw 唯讀、正負調整、destroy/reopen、成功／失敗與其他草稿。3 項因無 DISPLAY 明確跳過。
- 原 test_gui.py 主畫面測試 1 項跳過。Windows DPI、真實字型與板端 I/O 未驗證。
- 原 test_pid_settings.py 仍測同一封包、有號數／divisor、危險狀態與讀回不符；只將 Controller 測試呼叫更新為新的帶 ID 交易契約。
- 所有 Python AST 通過；protocol.py、pid_settings.py、units.py、calibration.py、report.py、summarize.py、theme.py 與 v0.3.23 位元組相同；PidDialog._styles／_group AST 相同。未改原始量測或韌體。

執行：`python -m unittest discover -v`。有桌面顯示的 Windows 環境可另外執行 `python -m unittest test_pid_gui -v`；主畫面 GUI 測試仍遵循原 ROBI_GUI_TESTS 設定。

## 交付與回復

解壓 Robi_Integrated_Automation_v0.3.24.zip 到獨立資料夾，沿用既有啟動腳本。回復時關閉新版，從保留的 v0.3.23 資料夾啟動；不回刷韌體。若新版期間已實際改過板端參數，切換軟體版本不會自動還原板端參數，必須重新讀取確認。

PID／PLL 實機驗證仍未完成；48 V 韌體修改、編譯、燒錄仍未完成。v0.3.24 是離線驗證完成的修正版，不是 Windows GUI／硬體驗收完成版。
