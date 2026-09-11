import { useEffect, useState } from "react"
import type { NotificationRiskPolicy as RiskPolicy } from "@/entities/project-notification/model/types"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Switch } from "@/shared/ui/switch"

const labels: Record<RiskPolicy["risk_level"], string> = {
  EXTREME: "Cực cao", VERY_HIGH: "Rất cao", HIGH: "Cao",
  MEDIUM: "Trung bình", LOW_MEDIUM: "Thấp–trung bình", LOW: "Thấp",
}

export function NotificationRiskPolicy({ policies, disabled, onChange }: {
  policies: RiskPolicy[]
  disabled: boolean
  onChange: (policies: RiskPolicy[]) => void
}) {
  const [draft, setDraft] = useState(policies)
  const [numbers, setNumbers] = useState(() => numericInputs(policies))
  useEffect(() => {
    setDraft(policies)
    setNumbers(numericInputs(policies))
  }, [policies])
  const update = (index: number, patch: Partial<RiskPolicy>) =>
    setDraft(current => current.map((policy, row) => row === index ? { ...policy, ...patch } : policy))
  const normalized = normalizeRiskPolicyDraft(draft, numbers)
  return <section className="rounded-lg border" aria-labelledby="telegram-risk-policy-title">
    <div className="p-4">
      <h3 id="telegram-risk-policy-title" className="font-medium">Chính sách theo mức rủi ro</h3>
      <p className="mt-1 text-sm text-muted-foreground">Tắt Telegram không dừng rule hoặc xóa sự cố. Thời gian được nhập theo phút.</p>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] text-sm">
        <thead className="border-y bg-muted/50 text-left"><tr>{["Mức độ", "Telegram", "Khi mở", "Tăng mức", "Phục hồi", "Đã xử lý", "Nhắc lại", "Nhắc đầu", "Chu kỳ", "Tối đa", "Dừng khi ACK"].map(value => <th key={value} className="p-2 font-medium">{value}</th>)}</tr></thead>
        <tbody>{draft.map((policy, index) => <tr key={policy.risk_level} className="border-b last:border-0">
          <td className="p-2 font-medium">{labels[policy.risk_level]}</td>
          {(["telegram_enabled", "notify_on_open", "notify_on_escalation", "notify_on_recovery", "notify_on_resolved", "reminder_enabled"] as const).map(field => <td key={field} className="p-2"><Switch aria-label={`${labels[policy.risk_level]} ${field}`} checked={policy[field]} disabled={disabled} onCheckedChange={checked => update(index, { [field]: checked })} /></td>)}
          <td className="p-2"><Input aria-label={`Nhắc đầu ${labels[policy.risk_level]}`} className="w-20" type="number" min={0} value={numbers[policy.risk_level].initial} disabled={disabled || !policy.reminder_enabled} onChange={event => setNumbers(current => ({ ...current, [policy.risk_level]: { ...current[policy.risk_level], initial: event.target.value } }))} /></td>
          <td className="p-2"><Input aria-label={`Chu kỳ ${labels[policy.risk_level]}`} className="w-20" type="number" min={0} value={numbers[policy.risk_level].repeat} disabled={disabled || !policy.reminder_enabled} onChange={event => setNumbers(current => ({ ...current, [policy.risk_level]: { ...current[policy.risk_level], repeat: event.target.value } }))} /></td>
          <td className="p-2"><Input aria-label={`Tối đa ${labels[policy.risk_level]}`} className="w-16" type="number" min={0} value={numbers[policy.risk_level].maximum} disabled={disabled || !policy.reminder_enabled} onChange={event => setNumbers(current => ({ ...current, [policy.risk_level]: { ...current[policy.risk_level], maximum: event.target.value } }))} /></td>
          <td className="p-2"><Switch aria-label={`Dừng ACK ${labels[policy.risk_level]}`} checked={policy.stop_reminders_on_ack} disabled={disabled || !policy.reminder_enabled} onCheckedChange={checked => update(index, { stop_reminders_on_ack: checked })} /></td>
        </tr>)}</tbody>
      </table>
    </div>
    <div className="flex items-center justify-between gap-3 p-4">
      <p className="text-xs text-muted-foreground">Các thay đổi chỉ được gửi một lần khi bấm lưu.</p>
      <Button disabled={disabled || !normalized} onClick={() => normalized && onChange(normalized)}>Lưu chính sách</Button>
    </div>
  </section>
}

type NumericDraft = Record<RiskPolicy["risk_level"], { initial: string; repeat: string; maximum: string }>

function numericInputs(policies: RiskPolicy[]): NumericDraft {
  return Object.fromEntries(policies.map(policy => [policy.risk_level, {
    initial: String(policy.initial_reminder_seconds / 60),
    repeat: String(policy.repeat_interval_seconds / 60),
    maximum: String(policy.max_reminders),
  }])) as NumericDraft
}

export function normalizeRiskPolicyDraft(policies: RiskPolicy[], values: NumericDraft): RiskPolicy[] | null {
  const normalized = policies.map(policy => {
    const initialMinutes = Number(values[policy.risk_level].initial)
    const repeatMinutes = Number(values[policy.risk_level].repeat)
    const maximum = Number(values[policy.risk_level].maximum)
    if (!values[policy.risk_level].initial.trim() || !values[policy.risk_level].repeat.trim() || !values[policy.risk_level].maximum.trim()) return null
    if (![initialMinutes, repeatMinutes, maximum].every(Number.isFinite) || !Number.isInteger(maximum) || maximum < 0) return null
    const initial = initialMinutes * 60
    const repeat = repeatMinutes * 60
    if (!Number.isInteger(initial) || !Number.isInteger(repeat) || initial < 0 || repeat < 0) return null
    if (policy.reminder_enabled && (initial <= 0 || repeat <= 0 || maximum <= 0)) return null
    return { ...policy, initial_reminder_seconds: initial, repeat_interval_seconds: repeat, max_reminders: maximum }
  })
  return normalized.every((policy): policy is RiskPolicy => policy !== null) ? normalized : null
}
