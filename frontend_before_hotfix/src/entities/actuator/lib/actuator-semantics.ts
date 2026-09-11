export function actuatorStateLabel(value: boolean | null) {
  return value === null ? "Chưa báo về" : value ? "Bật" : "Tắt";
}

export function desiredStateLabel(value: boolean | null) {
  return value === null
    ? "Chưa có yêu cầu"
    : value
      ? "Yêu cầu Bật"
      : "Yêu cầu Tắt";
}

export function desiredStateValueLabel(value: boolean | null) {
  return value === null ? "Chưa có" : value ? "Bật" : "Tắt";
}

export function synchronizationLabel(
  desired: boolean | null,
  reported: boolean | null,
) {
  if (desired === null || reported === null) return "Chưa xác định";
  return desired === reported ? "Đã đồng bộ" : "Chưa đồng bộ";
}

export function connectionLabel(value: string) {
  return value === "ONLINE"
    ? "Trực tuyến"
    : value === "OFFLINE"
      ? "Ngoại tuyến"
      : value === "DISABLED"
        ? "Vô hiệu hóa"
        : "Chờ kết nối";
}

export function commandStatusLabel(value: string | null | undefined) {
  if (!value) return "Chưa có";
  return (
    (
      {
        ACKNOWLEDGED: "Đã xác nhận",
        TIMEOUT: "Hết thời gian chờ",
        PENDING: "Đang chờ",
        FAILED: "Thất bại",
      } as Record<string, string>
    )[value] ?? value
  );
}
