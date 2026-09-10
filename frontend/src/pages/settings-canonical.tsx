import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BellRing, Copy, ExternalLink, Globe2, Save, Settings, Trash2 } from "lucide-react"
import { useNavigate, useOutletContext, useParams } from "react-router-dom"
import { deleteSystem, getAlertSettings, getPublicMonitoringSettings, queryKeys, updateAlertSettings, updatePublicMonitoringSettings, updateSystem } from "@/api/resources"
import type { AlertSettingsUpdate, AquaponicsSystem, AquaponicsSystemUpdate } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/shared/ui/alert-dialog"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"
import { AlertDeliveryRecipientsPanel } from "@/pages/alert-delivery"

export function SettingsPage() {
  const systemId = useParams().systemId ?? ""
  const validId = Boolean(systemId)
  const { system } = useOutletContext<{ system: AquaponicsSystem }>()
  const { can } = useAuth()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [systemDraft, setSystemDraft] = useState<AquaponicsSystemUpdate>({})
  const [alertDraft, setAlertDraft] = useState<AlertSettingsUpdate | null>(null)
  const alertSettings = useQuery({ queryKey: queryKeys.alertSettings(systemId), queryFn: () => getAlertSettings(systemId), enabled: validId })
  const publicSettings = useQuery({ queryKey: queryKeys.publicMonitoringSettings(systemId), queryFn: () => getPublicMonitoringSettings(systemId), enabled: validId })

  useEffect(() => { setSystemDraft({ name: system.name, location: system.location, description: system.description }) }, [system])
  useEffect(() => { if (alertSettings.data) setAlertDraft({ enabled: alertSettings.data.enabled, in_app_enabled: alertSettings.data.in_app_enabled, telegram_enabled: alertSettings.data.telegram_enabled }) }, [alertSettings.data])

  const saveSystem = useMutation({ mutationFn: () => updateSystem(systemId, systemDraft), onSuccess: async (value) => { client.setQueryData(queryKeys.system(systemId), value); await client.invalidateQueries({ queryKey: queryKeys.systems }) } })
  const removeSystem = useMutation({ mutationFn: () => deleteSystem(systemId), onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.systems }); navigate("/aquaponics-systems") } })
  const saveAlerts = useMutation({ mutationFn: () => updateAlertSettings(systemId, alertDraft ?? {}), onSuccess: async (value) => { client.setQueryData(queryKeys.alertSettings(systemId), value); setAlertDraft(value); await client.invalidateQueries({ queryKey: queryKeys.deliverySettings(systemId) }) } })
  const savePublic = useMutation({ mutationFn: (enabled: boolean) => updatePublicMonitoringSettings(systemId, enabled), onSuccess: (value) => client.setQueryData(queryKeys.publicMonitoringSettings(systemId), value) })

  if (!validId) return <EmptyState icon={Settings} title="Đường dẫn hệ thống không hợp lệ" description="System ID phải là số nguyên dương." />
  const alertValue = alertDraft ?? alertSettings.data

  return <div className="max-w-3xl space-y-6">
    <div><h2 className="text-xl font-semibold">Thiết lập hệ thống</h2><p className="text-sm text-muted-foreground">Metadata hệ thống và chính sách Alert được lưu qua canonical API.</p></div>
    <Card><CardHeader><CardTitle>Thông tin hệ thống</CardTitle></CardHeader><CardContent><form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); saveSystem.mutate() }}><div><p className="text-sm text-muted-foreground">Mã hệ thống</p><p className="mt-1 font-mono font-medium">{system.code}</p></div><TextField id="settings-name" label="Tên hệ thống" value={systemDraft.name ?? ""} onChange={(name) => setSystemDraft((current) => ({ ...current, name }))} /><TextField id="settings-location" label="Vị trí" required={false} value={systemDraft.location ?? ""} onChange={(location) => setSystemDraft((current) => ({ ...current, location }))} /><div><Label htmlFor="settings-description">Mô tả</Label><Textarea id="settings-description" className="mt-1" value={systemDraft.description ?? ""} onChange={(event) => setSystemDraft((current) => ({ ...current, description: event.target.value }))} /></div>{can("aquaponics_systems.update") ? <div className="flex justify-end sm:col-span-2"><Button type="submit" disabled={saveSystem.isPending}><Save />Lưu thông tin</Button></div> : null}{saveSystem.isError ? <p role="alert" className="text-sm text-destructive sm:col-span-2">{errorMessage(saveSystem.error)}</p> : null}</form></CardContent></Card>

    <Card><CardHeader><CardTitle className="flex items-center gap-2"><BellRing className="size-5 text-primary" />Kênh cảnh báo</CardTitle></CardHeader><CardContent className="space-y-5">{alertSettings.isLoading || !alertValue ? <Skeleton className="h-36" /> : alertSettings.isError ? <EmptyState icon={BellRing} title="Không thể tải thiết lập Alert" description={errorMessage(alertSettings.error)} /> : <>{([ ["enabled", "Gửi khi Alert mở", "Chính sách event OPEN; ngưỡng được bật/tắt riêng tại từng Sensor/Actuator"], ["in_app_enabled", "Thông báo trong ứng dụng", "Hiển thị Alert cho người vận hành"], ["telegram_enabled", "Gửi qua Telegram", "Chỉ hoạt động khi backend đã cấu hình bot và có người nhận"] ] as const).map(([key, label, description]) => <div className="flex items-center justify-between gap-4" key={key}><div><p className="font-medium">{label}</p><p className="text-sm text-muted-foreground">{description}</p></div><Switch checked={Boolean(alertValue[key])} disabled={!can("aquaponics_systems.update")} onCheckedChange={(checked) => setAlertDraft((current) => ({ ...current, [key]: checked }))} aria-label={label} /></div>)}{can("aquaponics_systems.update") ? <Button onClick={() => saveAlerts.mutate()} disabled={saveAlerts.isPending}><Save />Lưu thiết lập Alert</Button> : null}{saveAlerts.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(saveAlerts.error)}</p> : null}</>}</CardContent></Card>

    {can("notifications.settings.read") ? <AlertDeliveryRecipientsPanel /> : null}

    <Card><CardHeader><CardTitle className="flex items-center gap-2"><Globe2 className="size-5 text-primary" />Giám sát công khai</CardTitle></CardHeader><CardContent className="space-y-4">{publicSettings.isLoading ? <Skeleton className="h-24" /> : publicSettings.isError || !publicSettings.data ? <EmptyState icon={Globe2} title="Không thể tải cấu hình công khai" description={errorMessage(publicSettings.error)} /> : <><div className="flex items-center justify-between gap-4"><div><p className="font-medium">Cho phép xem chỉ đọc từ Internet</p><p className="text-sm text-muted-foreground">Không cho phép điều khiển, cấu hình, MQTT, thành viên hoặc Telegram.</p></div><Switch checked={publicSettings.data.enabled} disabled={!can("aquaponics_systems.update") || savePublic.isPending} onCheckedChange={(enabled) => savePublic.mutate(enabled)} aria-label="Bật giám sát công khai" /></div>{publicSettings.data.enabled && publicSettings.data.public_slug ? <div className="rounded-lg border p-4"><p className="text-sm font-medium">Đường dẫn công khai</p><code className="mt-2 block overflow-x-auto rounded bg-muted px-3 py-2 text-xs">{`${window.location.origin}/public/${publicSettings.data.public_slug}`}</code><div className="mt-3 flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => void navigator.clipboard.writeText(`${window.location.origin}/public/${publicSettings.data!.public_slug}`).then(() => {}, () => {})}><Copy />Sao chép</Button><Button asChild variant="outline"><a href={`/public/${publicSettings.data.public_slug}`} target="_blank" rel="noreferrer"><ExternalLink />Mở màn hình</a></Button></div></div> : null}{savePublic.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(savePublic.error)}</p> : null}</>}</CardContent></Card>

    {can("aquaponics_systems.delete") ? <Card className="border-destructive/30"><CardHeader><CardTitle className="text-destructive">Vùng nguy hiểm</CardTitle></CardHeader><CardContent className="flex flex-wrap items-center justify-between gap-4"><div><p className="font-medium">Xoá hệ thống</p><p className="text-sm text-muted-foreground">Chỉ thực hiện khi hệ thống và dữ liệu liên quan có thể được xoá theo chính sách backend.</p></div><AlertDialog><AlertDialogTrigger asChild><Button variant="destructive"><Trash2 />Xoá hệ thống</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Xoá {system.name}?</AlertDialogTitle><AlertDialogDescription>Đây là thao tác không thể hoàn tác từ giao diện. Backend sẽ từ chối nếu còn ràng buộc không cho phép xoá.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Huỷ</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={() => removeSystem.mutate()}>Xác nhận xoá</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>{removeSystem.isError ? <p role="alert" className="w-full text-sm text-destructive">{errorMessage(removeSystem.error)}</p> : null}</CardContent></Card> : null}
  </div>
}

function TextField({ id, label, value, onChange, required = true }: { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required={required} /></div> }
