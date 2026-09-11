import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { NotificationSettings } from "@/entities/project-notification/model/types"
import { NotificationRiskPolicy, normalizeRiskPolicyDraft } from "@/features/manage-project-notifications/NotificationRiskPolicy"

const data: NotificationSettings = {
  telegram_enabled: true,
  telegram_bot_configured: true,
  notify_alert_opened: true,
  notify_alert_escalated: true,
  notify_alert_reminder: false,
  reminder_interval_minutes: null,
  notify_alert_recovered: true,
  notify_alert_resolved: true,
  minimum_business_risk_level: "LOW",
  risk_extreme_enabled: true,
  risk_very_high_enabled: true,
  risk_high_enabled: true,
  risk_medium_enabled: false,
  risk_low_medium_enabled: false,
  risk_low_enabled: false,
  risk_policies: (["EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"] as const).map((risk_level, index) => ({
    risk_level, telegram_enabled: index < 4, notify_on_open: true,
    notify_on_escalation: true, notify_on_recovery: true, notify_on_resolved: true,
    reminder_enabled: index < 3, initial_reminder_seconds: 300,
    repeat_interval_seconds: 600, max_reminders: index < 3 ? 4 : 0,
    stop_reminders_on_ack: true,
  })),
  recipients: [],
}

describe("NotificationRiskPolicy", () => {
  it("hiển thị sáu mức nghiệp vụ và trạng thái độc lập bằng tiếng Việt", () => {
    const markup = renderToStaticMarkup(<NotificationRiskPolicy policies={data.risk_policies} disabled={false} onChange={() => undefined} />)
    for (const label of ["Cực cao", "Rất cao", "Cao", "Trung bình", "Thấp–trung bình", "Thấp"]) expect(markup).toContain(label)
    expect(markup.match(/role="switch"/g)).toHaveLength(42)
    expect(markup).toContain("Tắt Telegram không dừng rule hoặc xóa sự cố")
    expect(markup).toContain("Dừng khi ACK")
    expect(markup).toContain("Lưu chính sách")
  })

  it("chỉ chuẩn hóa số khi lưu và từ chối ô trống của reminder đang bật", () => {
    const values = Object.fromEntries(data.risk_policies.map(policy => [policy.risk_level, {
      initial: "5", repeat: "10", maximum: policy.reminder_enabled ? "4" : "0",
    }])) as Parameters<typeof normalizeRiskPolicyDraft>[1]
    const normalized = normalizeRiskPolicyDraft(data.risk_policies, values)
    expect(normalized?.[0].initial_reminder_seconds).toBe(300)
    expect(normalized?.[0].repeat_interval_seconds).toBe(600)
    expect(normalized?.[0].max_reminders).toBe(4)
    expect(normalizeRiskPolicyDraft(data.risk_policies, {
      ...values, VERY_HIGH: { ...values.VERY_HIGH, initial: "" },
    })).toBeNull()
  })
})
