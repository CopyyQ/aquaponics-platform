import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BellRing, Save } from "lucide-react"
import { useParams } from "react-router-dom"
import { getAlertSettings, queryKeys, updateAlertSettings } from "@/api/resources"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { Switch } from "@/shared/ui/switch"
import { errorMessage } from "@/api/client"

export function SettingsPage() {
  const systemId = useParams().systemId ?? ""; const { can } = useAuth(); const client = useQueryClient(); const settings = useQuery({ queryKey: queryKeys.alertSettings(systemId), queryFn: () => getAlertSettings(systemId), enabled: Boolean(systemId) }); const [draft, setDraft] = useState<{ enabled: boolean; in_app_enabled: boolean; telegram_enabled: boolean } | null>(null)
  const save = useMutation({ mutationFn: () => updateAlertSettings(systemId, draft ?? settings.data!), onSuccess: (value) => { client.setQueryData(queryKeys.alertSettings(systemId), value); setDraft(null) } })
  if (settings.isLoading) return <Skeleton className="h-80" />
  if (settings.isError || !settings.data) return <EmptyState icon={BellRing} title="Không thể tải thiết lập" description={errorMessage(settings.error)} />
  const value = draft ?? settings.data
  return <div className="max-w-2xl space-y-5"><div><h2 className="text-xl font-semibold">Thiết lập cảnh báo</h2><p className="text-sm text-muted-foreground">Chính sách hệ thống tách biệt với kênh Telegram cá nhân.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><BellRing className="size-5 text-primary" />Kênh thông báo</CardTitle></CardHeader><CardContent className="space-y-5">{([ ["enabled", "Đánh giá điều kiện cảnh báo", "Bật hoặc tắt việc đánh giá ngưỡng"], ["in_app_enabled", "Thông báo trong ứng dụng", "Hiển thị cảnh báo cho người vận hành"], ["telegram_enabled", "Gửi qua Telegram", "Chỉ hoạt động khi backend có cấu hình kênh"] ] as const).map(([key, label, description]) => <div className="flex items-center justify-between gap-4" key={key}><div><p className="font-medium">{label}</p><p className="text-sm text-muted-foreground">{description}</p></div><Switch checked={value[key]} disabled={!can("aquaponics_systems.update")} onCheckedChange={(checked) => setDraft({ ...value, [key]: checked })} aria-label={label} /></div>)}{can("aquaponics_systems.update") ? <Button onClick={() => save.mutate()} disabled={!draft || save.isPending}><Save />Lưu thiết lập</Button> : null}</CardContent></Card></div>
}
