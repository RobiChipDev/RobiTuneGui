# Robi Integrated Automation v0.3.29

Python / Tkinter 馬達與螺旋槳量測平台，整合馬達通訊、力規、電供唯讀監看及測次資料輸出。
此目錄是獨立應用程式；執行前請切換至本目錄。Repo 根目錄的既有 RobiTuneGui 程式維持原樣。

## 安裝與啟動（Windows）

1. 安裝含 Tcl/Tk 與 Python Launcher 的 Python 3；實際 Windows / Python 版本請在交接驗收填寫。
2. 在本目錄執行 `install_windows.bat` 安裝依賴，再執行 `start_windows.bat`。
3. 等效命令：

```powershell
py -3 -m pip install -r requirements.txt
py -3 app.py
```

隨附依賴為 `pyserial==3.5` 與 `pyvisa>=1.14,<2`。SERIAL 與 VISA 為不同電供存取路徑；若使用 VISA，還需確認現場 VISA backend / 驅動。
首次啟動維持模擬模式，先核對畫面及存檔，再依現場驗收流程解除實機鎖定。軟體安裝不會替設備安裝驅動或燒錄韌體。

## 設備設定與資料

| 設備 | 程式預設 | 換電腦時需確認 |
|---|---|---|
| 馬達通訊 | COM5 | 實際 COM、設備驅動、板端韌體與通訊相容性 |
| 力規 | COM6 / 9600 baud | 站號、字序、通道、校正與零點 |
| 電供擷取 | 預設停用 / SERIAL /  / 115200 baud | 實際 COM 或 VISA 資源、面板讀值及通道 |

- 力規 CH1 預設推力 N，倍率 0.01；力規 CH2 預設扭矩 N·m，倍率 0.001。電供 CH1 / CH2 是另一套通道。
- 電供介面是唯讀擷取；套用擷取設定不設定實體輸出電壓、限流或輸出開關。
- 預設工作資料夾為使用者的 `Documents/Robi`，包含 `ExperimentData`、`ExperimentSettings` 與 `DeviceSettings`。現場資料留在工作資料夾，不隨每次程式更新覆蓋。
- 測次保留原始 CSV、設定 JSON、摘要 CSV、分階段 CSV 與 HTML 報告；缺測與失聯不得改成有效零值。
- 不同電腦的 COM 號及已儲存的設定可能不同；載入舊設定後仍需核對。

## 操作文件

- [完整歷史操作說明](README_先看這裡.md)：含歸零、方向換算、PID / PLL 與輸出規則；歷史版本敘述不代表本版完成度。
- [變更紀錄](CHANGELOG.md)
- [本版發布說明](RELEASE_v0.3.29.md)
- [驗證紀錄](VALIDATION.md)
- [交接狀態](HANDOVER_STATUS.md)
- [協定來源](PROTOCOL_SOURCES.md)

## 驗證與限制

- 本版狀態以本版發布說明為準，離線測試、Windows GUI / DPI 與實機驗收分開記錄。
- 本次匯入準備未重跑 v0.3.29；原包的歷史測試輸出保留於 validation。
- 本次未驗證 Windows GUI、實體 USB / COM、PID / PLL 板端讀寫、跨電腦執行包，亦未操作硬體或燒錄韌體。
- TA612C 通訊尚未整合；板端溫度不是線圈最高溫量測。
- STOP 指令送出不等於已機械停穩。既有現場紀錄曾有通訊失聯後馬達持續轉動；板端失聯停機能力需另行確認，軟體 STOP 不能替代現場獨立停機方式。
- 7100 rpm 為軟體輸入上限，不能當作機械安全轉速。
- 這是原始碼交付，不是已驗證的 Windows EXE。

## 執行離線回歸

在本目錄執行：

```powershell
py -3 -m unittest discover -v
```

未具備測試顯示環境的 GUI 案例會跳過，跳過項目不算驗收通過。不要為了讓測試全綠而連接實驗設備。
