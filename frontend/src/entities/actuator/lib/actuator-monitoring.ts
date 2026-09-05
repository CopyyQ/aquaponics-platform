export type ActuatorCommandTone = "neutral" | "warning" | "success" | "danger"

export function getDesiredStateLabel(state: boolean | null) {
  if (state === null) return "Chưa có yêu cầu"
  return state ? "Yêu cầu bật" : "Yêu cầu tắt"
}

export function getReportedStateLabel(state: boolean | null) {
  if (state === null) return "Chưa xác định"
  return state ? "Đang bật" : "Đang tắt"
}

export function getCommandStatus(
  status: string | null,
): { label: string; tone: ActuatorCommandTone; active: boolean } {
  if (status === "PENDING") {
    return { label: "Đang chờ gửi", tone: "warning", active: true }
  }
  if (status === "PUBLISHED") {
    return { label: "Đang chờ thiết bị xác nhận", tone: "warning", active: true }
  }
  if (status === "ACKNOWLEDGED") {
    return { label: "Thành công", tone: "success", active: false }
  }
  if (status === "FAILED") {
    return { label: "Thất bại", tone: "danger", active: false }
  }
  if (status === "TIMEOUT") {
    return { label: "Hết thời gian chờ", tone: "danger", active: false }
  }
  return { label: "Chưa có lệnh", tone: "neutral", active: false }
}

export function isAwaitingActuatorConfirmation(
  desiredState: boolean | null,
  reportedState: boolean | null,
  commandStatus: string | null,
) {
  return desiredState !== null
    && desiredState !== reportedState
    && getCommandStatus(commandStatus).active
}
