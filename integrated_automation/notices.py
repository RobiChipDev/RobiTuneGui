"""Operator-facing labels for controller outcomes."""
ABORTS = {'operator_stop', 'operator_stop_before_start', 'application_close', 'disconnect_requested'}
ERRORS = {
    'motor_fault': '馬達控制器回報故障',
    'speed_not_reached': '未在期限內達到目標轉速',
    'speed_deviation': '轉速偏離目標',
    'motor_unavailable': '無法取得馬達狀態',
    'motor_communication_error': '馬達通訊異常',
    'startup_timeout': '馬達啟動逾時',
    'sensor_stale': '感測器資料更新逾時',
    'sensor_preflight_timeout': '感測器啟動檢查逾時',
    'sensor_queue_overflow': '感測器資料佇列已滿',
    'unexpected_motor_motion': '偵測到非預期的馬達運轉',
    'unexpected_non_RUN': '馬達離開運轉狀態',
    'force_error': '力規擷取異常',
    'psu_error': '電源供應器擷取異常',
    'validation_error': '實驗設定驗證失敗',
    'controller_error': '控制程式執行異常',
    'stop_state_unconfirmed': '未能確認控制器停止狀態',
}


def fault_label(code):
    return f'驅動器保護故障（{code:#x}）' if code == 0x400 else f'控制器故障（{code:#x}）'


def outcome_label(detail):
    reason, _, extra = detail.partition(' ')
    if not reason or reason == 'sequence_complete':
        return ''
    if reason in ABORTS:
        return '已中止'
    if reason == 'motor_fault' and extra.startswith('0x'):
        return fault_label(int(extra, 16))
    return ERRORS.get(reason, f'量測異常（{reason}）')
