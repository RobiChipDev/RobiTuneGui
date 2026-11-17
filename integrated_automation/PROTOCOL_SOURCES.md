# 協定依據與驗證範圍

## 電供
GW Instek官方GPP-3060/GPP-6030/GPP-3650 User Manual，官網標示B版，下載頁2024-06-25。
產品頁：https://www.gwinstek.com/en-global/products/detail/GPP-3060_6030
手冊：https://www.gwinstek.com/en-global/products/downloadSeriesDownNew/21821/2123

- 印刷頁104–105：USB CDC、鮑率、驅動與面板自動鎖定。
- 印刷頁127：`:MEASure[1|2|3]:<function>?`，電流CURRent、電壓VOLTage、功率POWEr。
- 印刷頁196：`*IDN?`廠商、型號、序號、版本四欄位。
- 指令終止LF，回覆LF（Remote Control / Command Terminators）。

本版只允許下列查詢（依通道1/2替換）：
`*IDN?`
`:MEAS1:VOLT?`、`:MEAS1:CURR?`、`:MEAS1:POWE?`
`:MEAS2:VOLT?`、`:MEAS2:CURR?`、`:MEAS2:POWE?`
`:SOUR1:VOLT?`、`:SOUR1:CURR?`、`:SOUR1:CURR:STAT?`（2號通道同理；實際命令使用ASCII冒號）。
印刷頁136–138：設定電壓、設定限流、限流狀態查詢。
不傳任何寫入、輸出開關、重設、清錯或LOCAL等命令。
未實機確認回覆格式與連線參數；上機需先以型號回覆核對。模型測試驗證查詢語法，不能代替真實設備測試。

## 馬達與力規
馬達協定沿用v0.2，依使用者提供RC100D_Rum3848yMotorTest的MCSDK6.4.2韌體Src、Inc、ASPEP/MCP定義核對。
力規依使用者提供RDT-T2S手冊印刷頁10、28、29，03功能碼讀450/452各兩暫存器，32位元有號整數，CRC16 Modbus。
v0.1獨立力規工具已有使用者實機CSV確認成功，v0.3完整整合版仍待使用者實機測試。

## v0.3離線驗證
以實際執行test*.py的結果為準；沒有可用Windows桌面與實驗硬體，因此未宣稱GUI或硬體驗證通過。

## v0.3.1額外STM32讀值
集中暫存器編號位於protocol.py REG。依Inc/register_interface.h與Src/sync_registers.c：
- 16bit元素22：VBS_GetAvBusVoltage_V，無號整數V。
- 16bit元素23：NTC_GetAvTemp_C，有號整數°C，感測點不是由此API保證為MCU內部。
- 32bit元素109：PQD_GetAvrgElMotorPowerW，float32位元表示；不能用普通int32解析。
- 16bit元素35/36：Iq/Id有號原始值；RAW元素4 SCALE_CONFIG回覆size=12與float32的voltage/current/frequency，current作為A/count。
- Src/mc_parameters.c與Inc/mc_interface.h說明係數與欄位排列。每次連線讀板上係數，保存JSON與原始CSV，不固定寫死A換算值。
溫度來源目前上傳程式mc_config_common.c使用REAL_SENSOR；實際上板韌體與感測硬體仍須上機確認。
