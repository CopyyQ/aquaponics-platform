import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BellRing, Pencil, Plus, Send, Trash2 } from "lucide-react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import {
  addAlertDeliveryRecipient,
  deleteAlertDeliveryRecipient,
  getAlertDeliveryHistory,
  getAlertDeliverySettings,
  queryKeys,
  testAlertDeliveryRecipient,
  updateAlertDeliveryRecipient,
  updateAlertDeliverySettings,
} from "@/api/resources"
import type { AlertDeliveryRecipient, AlertDeliverySettings, NotificationRiskPolicy, RiskLevel } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function AlertDeliveryPage() {
  return <AlertDeliveryManager showHeading showPolicy showRecipients showHistory />
}

/**
 * Reusable recipient manager for System Settings.
 * The old frontend exposed recipient management as a first-class capability;
 * keeping it here avoids hiding Telegram destination configuration behind a
 * separate route while still retaining /notifications for the full history UI.
 */
export function AlertDeliveryRecipientsPanel() {
  return <AlertDeliveryManager showHeading={false} showPolicy={false} showRecipients showHistory={false} />
}

function AlertDeliveryManager({
  showHeading,
  showPolicy,
  showRecipients,
  showHistory,
}: {
  showHeading: boolean
  showPolicy: boolean
  showRecipients: boolean
  showHistory: boolean
}) {
  const systemId = Number(useParams().systemId)
  const client = useQueryClient()
  const { can } = useAuth()
  const [editing, setEditing] = useState<AlertDeliveryRecipient | "new" | null>(null)

  const settings = useQuery({
    queryKey: queryKeys.deliverySettings(systemId),
    queryFn: () => getAlertDeliverySettings(systemId),
    enabled: systemId > 0 && can("notifications.settings.read"),
  })
  const history = useQuery({
    queryKey: queryKeys.deliveryHistory(systemId),
    queryFn: () => getAlertDeliveryHistory(systemId),
    enabled: systemId > 0 && showHistory && can("notifications.history.read"),
  })
  const save = useMutation({
    mutationFn: (next: AlertDeliverySettings) => updateAlertDeliverySettings(systemId, next),
    onSuccess: async (data) => {
      client.setQueryData(queryKeys.deliverySettings(systemId), data)
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.alertSettings(systemId) }),
        client.invalidateQueries({ queryKey: queryKeys.deliveryHistory(systemId) }),
      ])
      toast.success("Đã lưu cấu hình gửi cảnh báo")
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  if (!can("notifications.settings.read")) {
    return <EmptyState icon={BellRing} title="Không có quyền xem kênh cảnh báo" description="Tài khoản hiện tại không có quyền notifications.settings.read." />
  }
  if (settings.isLoading) return <Skeleton className="h-[24rem]" />
  if (settings.isError || !settings.data) {
    return <EmptyState icon={BellRing} title="Không thể tải kênh cảnh báo" description={errorMessage(settings.error)} />
  }

  const data = settings.data
  const patch = (value: Partial<AlertDeliverySettings>) => save.mutate({ ...data, ...value })
  const patchRiskPolicy = (riskLevel: RiskLevel, value: Partial<NotificationRiskPolicy>) => save.mutate({
    ...data,
    risk_policies: data.risk_policies.map((policy) => policy.risk_level === riskLevel ? { ...policy, ...value } : policy),
  })
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: queryKeys.deliverySettings(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.deliveryHistory(systemId) }),
    ])
  }

  return <div className="space-y-6">
    {showHeading ? <div><h2 className="text-2xl font-bold">Thông báo & Telegram</h2><p className="text-sm text-muted-foreground">Quản lý chính sách gửi cảnh báo, người nhận Telegram và lịch sử gửi của hệ thống.</p></div> : null}

    {showPolicy ? <Card><CardHeader><div className="flex items-start justify-between gap-3"><div className="min-w-0"><CardTitle>Thông báo & Telegram</CardTitle><CardDescription>Bot token chỉ tồn tại ở backend; trình duyệt quản lý kênh, event và chính sách theo mức rủi ro. Generation hiện tại: {data.notification_generation}.</CardDescription></div><StatusBadge value={data.telegram_bot_configured ? "CONFIGURED" : "NOT_CONFIGURED"} /></div></CardHeader><CardContent className="space-y-5">
      <Setting label="Bật hệ thống thông báo" checked={data.enabled} disabled={!can("notifications.settings.update") || save.isPending} onChange={(enabled) => patch({ enabled })} />
      <Setting label="Bật thông báo trong ứng dụng" checked={data.in_app_enabled} disabled={!can("notifications.settings.update") || save.isPending} onChange={(in_app_enabled) => patch({ in_app_enabled })} />
      <Setting label="Bật gửi Telegram" checked={data.telegram_enabled} disabled={!can("notifications.settings.update") || save.isPending} onChange={(telegram_enabled) => patch({ telegram_enabled })} />
      <Setting label="Gửi khi Alert mở" checked={data.notify_alert_opened} disabled={!can("notifications.settings.update") || save.isPending} onChange={(notify_alert_opened) => patch({ notify_alert_opened })} />
      <Setting label="Gửi khi Alert escalated" checked={data.notify_alert_escalated} disabled={!can("notifications.settings.update") || save.isPending} onChange={(notify_alert_escalated) => patch({ notify_alert_escalated })} />
      <Setting label="Gửi khi điều kiện hồi phục" checked={data.notify_alert_recovered} disabled={!can("notifications.settings.update") || save.isPending} onChange={(notify_alert_recovered) => patch({ notify_alert_recovered })} />
      <Setting label="Gửi khi Alert resolved" checked={data.notify_alert_resolved} disabled={!can("notifications.settings.update") || save.isPending} onChange={(notify_alert_resolved) => patch({ notify_alert_resolved })} />
      <Setting label="Bật reminder toàn cục" checked={data.notify_alert_reminder} disabled={!can("notifications.settings.update") || save.isPending} onChange={(notify_alert_reminder) => patch({ notify_alert_reminder })} />
      <div className="border-t pt-4"><p className="font-medium">Chính sách theo mức rủi ro</p><p className="mb-3 text-sm text-muted-foreground">Một Alert chỉ được gửi khi cả kênh Telegram, event và mức rủi ro tương ứng đều được bật. ACTIVE_SYNC dùng chính sách OPEN khi cấu hình được bật lại.</p><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Mức rủi ro</TableHead><TableHead>Telegram</TableHead><TableHead>OPEN / ACTIVE_SYNC</TableHead><TableHead>Escalated</TableHead><TableHead>Recovery</TableHead><TableHead>Resolved</TableHead><TableHead>Reminder</TableHead></TableRow></TableHeader><TableBody>{data.risk_policies.map((policy) => <TableRow key={policy.risk_level}><TableCell className="font-medium"><StatusBadge value={policy.risk_level} /></TableCell><TableCell><Switch checked={policy.telegram_enabled} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(telegram_enabled) => patchRiskPolicy(policy.risk_level, { telegram_enabled })} aria-label={`Telegram ${policy.risk_level}`} /></TableCell><TableCell><Switch checked={policy.notify_on_open} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(notify_on_open) => patchRiskPolicy(policy.risk_level, { notify_on_open })} aria-label={`Alert mở ${policy.risk_level}`} /></TableCell><TableCell><Switch checked={policy.notify_on_escalation} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(notify_on_escalation) => patchRiskPolicy(policy.risk_level, { notify_on_escalation })} aria-label={`Escalated ${policy.risk_level}`} /></TableCell><TableCell><Switch checked={policy.notify_on_recovery} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(notify_on_recovery) => patchRiskPolicy(policy.risk_level, { notify_on_recovery })} aria-label={`Hồi phục ${policy.risk_level}`} /></TableCell><TableCell><Switch checked={policy.notify_on_resolved} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(notify_on_resolved) => patchRiskPolicy(policy.risk_level, { notify_on_resolved })} aria-label={`Resolved ${policy.risk_level}`} /></TableCell><TableCell><Switch checked={policy.reminder_enabled} disabled={!can("notifications.settings.update") || save.isPending} onCheckedChange={(reminder_enabled) => patchRiskPolicy(policy.risk_level, { reminder_enabled, max_reminders: reminder_enabled ? Math.max(1, policy.max_reminders) : policy.max_reminders, initial_reminder_seconds: reminder_enabled ? Math.max(60, policy.initial_reminder_seconds) : policy.initial_reminder_seconds, repeat_interval_seconds: reminder_enabled ? Math.max(60, policy.repeat_interval_seconds) : policy.repeat_interval_seconds })} aria-label={`Reminder ${policy.risk_level}`} /></TableCell></TableRow>)}</TableBody></Table></div></div>
    </CardContent></Card> : null}

    {showRecipients ? <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>Người nhận Telegram</CardTitle><CardDescription>Mỗi hệ thống có danh sách Telegram Chat ID riêng. ID có thể là người dùng hoặc nhóm/supergroup.</CardDescription></div>{can("notifications.recipients.create") ? <Button onClick={() => setEditing("new")}><Plus />Thêm người nhận</Button> : null}</div></CardHeader><CardContent>{data.recipients.length ? <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Tên</TableHead><TableHead>Telegram Chat ID</TableHead><TableHead>Trạng thái</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader><TableBody>{data.recipients.map((recipient) => <RecipientRow key={recipient.id} systemId={systemId} recipient={recipient} refresh={refresh} onEdit={() => setEditing(recipient)} />)}</TableBody></Table></div> : <EmptyState icon={Send} title="Chưa có người nhận Telegram" description="Thêm Telegram Chat ID để hệ thống có đích gửi Alert." action={can("notifications.recipients.create") ? <Button onClick={() => setEditing("new")}><Plus />Thêm người nhận</Button> : undefined} />}</CardContent></Card> : null}

    {showHistory && can("notifications.history.read") ? <Card><CardHeader><CardTitle>Lịch sử gửi</CardTitle><CardDescription>Hiển thị cả lần gửi thành công, thất bại và bị bỏ qua cùng nguyên nhân cụ thể.</CardDescription></CardHeader><CardContent>{history.isLoading ? <Skeleton className="h-48" /> : history.isError ? <EmptyState icon={BellRing} title="Không thể tải lịch sử gửi" description={errorMessage(history.error)} /> : history.data?.length ? <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Thời gian</TableHead><TableHead>Event</TableHead><TableHead>Rủi ro</TableHead><TableHead>Người nhận</TableHead><TableHead>Trạng thái</TableHead><TableHead>Số lần thử</TableHead><TableHead>Lý do / lỗi</TableHead></TableRow></TableHeader><TableBody>{history.data.map((item) => <TableRow key={item.id}><TableCell className="whitespace-nowrap">{new Date(item.created_at).toLocaleString("vi-VN")}</TableCell><TableCell className="font-mono text-xs">{item.event_type}</TableCell><TableCell>{item.risk ? <StatusBadge value={item.risk} /> : "—"}</TableCell><TableCell><span className="break-words">{item.recipient_name}</span></TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell>{item.attempt_count}</TableCell><TableCell className="max-w-80 text-xs"><span className="font-mono">{item.skip_reason ?? item.error_code ?? item.reason ?? "—"}</span>{item.error_message ? <p className="mt-1 break-words text-muted-foreground">{item.error_message}</p> : null}</TableCell></TableRow>)}</TableBody></Table></div> : <EmptyState icon={BellRing} title="Chưa có lịch sử gửi" description="Các lần gửi Alert sẽ xuất hiện tại đây." />}</CardContent></Card> : null}

    <RecipientDialog key={editing === "new" ? "new" : editing?.id ?? "closed"} systemId={systemId} value={editing} onClose={() => setEditing(null)} onSaved={refresh} />
  </div>
}

function Setting({ label, checked, disabled, onChange }: { label: string; checked: boolean; disabled: boolean; onChange: (value: boolean) => void }) {
  return <div className="flex items-center justify-between gap-4"><p className="font-medium">{label}</p><Switch checked={checked} disabled={disabled} onCheckedChange={onChange} aria-label={label} /></div>
}

function RecipientRow({ systemId, recipient, refresh, onEdit }: { systemId: number; recipient: AlertDeliveryRecipient; refresh: () => Promise<void>; onEdit: () => void }) {
  const { can } = useAuth()
  const update = useMutation({ mutationFn: (enabled: boolean) => updateAlertDeliveryRecipient(systemId, recipient.id, { enabled }), onSuccess: refresh, onError: (error) => toast.error(errorMessage(error)) })
  const remove = useMutation({ mutationFn: () => deleteAlertDeliveryRecipient(systemId, recipient.id), onSuccess: refresh, onError: (error) => toast.error(errorMessage(error)) })
  const test = useMutation({ mutationFn: () => testAlertDeliveryRecipient(systemId, recipient.id), onSuccess: (result) => toast.success(result.detail), onError: (error) => toast.error(errorMessage(error)) })
  return <TableRow><TableCell className="font-medium">{recipient.name}</TableCell><TableCell className="font-mono">{recipient.telegram_chat_id}</TableCell><TableCell><Switch checked={recipient.enabled} disabled={!can("notifications.recipients.update") || update.isPending} onCheckedChange={(enabled) => update.mutate(enabled)} aria-label={`${recipient.enabled ? "Tắt" : "Bật"} ${recipient.name}`} /></TableCell><TableCell><div className="flex justify-end gap-2">{can("notifications.recipients.test") ? <Button size="sm" variant="outline" onClick={() => test.mutate()} disabled={!recipient.enabled || test.isPending}><Send />Gửi thử</Button> : null}{can("notifications.recipients.update") ? <Button size="icon" variant="outline" onClick={onEdit} aria-label={`Sửa ${recipient.name}`}><Pencil /></Button> : null}{can("notifications.recipients.delete") ? <Button size="icon" variant="destructive" onClick={() => { if (window.confirm(`Xoá ${recipient.name}?`)) remove.mutate() }} aria-label={`Xoá ${recipient.name}`}><Trash2 /></Button> : null}</div></TableCell></TableRow>
}

function RecipientDialog({ systemId, value, onClose, onSaved }: { systemId: number; value: AlertDeliveryRecipient | "new" | null; onClose: () => void; onSaved: () => Promise<void> }) {
  const source = value && value !== "new" ? value : null
  const [name, setName] = useState(source?.name ?? "")
  const [chatId, setChatId] = useState(source?.telegram_chat_id ?? "")
  const mutation = useMutation({
    mutationFn: () => value === "new" ? addAlertDeliveryRecipient(systemId, { name: name.trim(), telegram_chat_id: chatId.trim() }) : updateAlertDeliveryRecipient(systemId, source!.id, { name: name.trim(), telegram_chat_id: chatId.trim() }),
    onSuccess: async () => { await onSaved(); toast.success(value === "new" ? "Đã thêm người nhận" : "Đã cập nhật người nhận"); onClose() },
    onError: (error) => toast.error(errorMessage(error)),
  })
  return <Dialog open={value !== null} onOpenChange={(open) => { if (!open) onClose() }}><DialogContent><DialogHeader><DialogTitle>{value === "new" ? "Thêm người nhận Telegram" : "Sửa người nhận Telegram"}</DialogTitle><DialogDescription>Nhập tên gợi nhớ và Telegram Chat ID. Nhóm/supergroup thường có Chat ID âm.</DialogDescription></DialogHeader><div className="space-y-4"><div><Label htmlFor="delivery-name">Tên người nhận</Label><Input id="delivery-name" className="mt-1" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ví dụ: Nhóm vận hành" /></div><div><Label htmlFor="delivery-chat">Telegram Chat ID</Label><Input id="delivery-chat" className="mt-1 font-mono" value={chatId} onChange={(event) => setChatId(event.target.value)} placeholder="Ví dụ: -1001234567890" /></div></div><DialogFooter><Button variant="outline" onClick={onClose}>Huỷ</Button><Button disabled={!name.trim() || !chatId.trim() || mutation.isPending} onClick={() => mutation.mutate()}>Lưu</Button></DialogFooter></DialogContent></Dialog>
}
