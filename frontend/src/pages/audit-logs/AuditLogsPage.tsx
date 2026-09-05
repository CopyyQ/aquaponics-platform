import { useQuery } from "@tanstack/react-query"
import { BellRing, BookOpenCheck, Settings2 } from "lucide-react"
import { Link } from "react-router-dom"
import { projectNotificationApi } from "@/entities/project-notification/api/project-notification-api"
import { auditApi } from "@/entities/audit/api/audit-api"
import { auditActionLabels, auditEntityLabels, formatAuditDetail } from "@/entities/audit/lib/audit-format"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs"

const deliveryLabels = { PENDING: "Đang chờ", SENT: "Đã gửi", FAILED: "Gửi thất bại", RETRYING: "Đang thử lại", SKIPPED: "Đã bỏ qua" } as const
const reasonLabels: Record<string, string> = { POLICY_DISABLED: "Chính sách của mức rủi ro đã tắt", SUPPRESSED_BY_DEVICE_OFFLINE: "Đã chặn thông báo phụ vì thiết bị đang ngoại tuyến" }
const riskLabels = { EXTREME: "Cực cao", VERY_HIGH: "Rất cao", HIGH: "Cao", MEDIUM: "Trung bình", LOW_MEDIUM: "Thấp–trung bình", LOW: "Thấp" } as const

export function AuditLogsPage() {
  const audit = useQuery({ queryKey: queryKeys.auditLogs, queryFn: auditApi.list })
  const deliveries = useQuery({ queryKey: ["notification-deliveries"], queryFn: projectNotificationApi.deliveryHistory })
  return <div className="flex flex-col gap-6"><PageHeader title="Thông báo & Nhật ký" description="Cấu hình kênh gửi, theo dõi từng lần gửi và tra cứu thay đổi hệ thống." /><Tabs defaultValue="history"><TabsList className="h-auto flex-wrap"><TabsTrigger value="settings">Cấu hình thông báo</TabsTrigger><TabsTrigger value="history">Lịch sử thông báo</TabsTrigger><TabsTrigger value="audit">Nhật ký hệ thống</TabsTrigger></TabsList>
    <TabsContent value="settings"><Card><CardHeader><CardTitle>Cấu hình thông báo theo dự án</CardTitle><CardDescription>Người nhận và lựa chọn sự kiện gửi vẫn được giới hạn trong từng dự án.</CardDescription></CardHeader><CardContent><div className="flex flex-wrap items-center justify-between gap-4 rounded-md border p-4"><div><p className="font-medium">Telegram và người nhận</p><p className="text-sm text-muted-foreground">Mở một dự án, chọn “Thông báo” để cấu hình mức cảnh báo, sự kiện mở, tăng mức, nhắc lại và phục hồi.</p></div><Button asChild><Link to="/projects"><Settings2 aria-hidden="true" />Chọn dự án</Link></Button></div></CardContent></Card></TabsContent>
    <TabsContent value="history">{deliveries.data?.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Thời gian</TableHead><TableHead>Dự án</TableHead><TableHead>Cảnh báo</TableHead><TableHead>Mức độ</TableHead><TableHead>Kênh</TableHead><TableHead>Người nhận</TableHead><TableHead>Trạng thái</TableHead><TableHead>Lý do</TableHead><TableHead>Số lần thử</TableHead></TableRow></TableHeader><TableBody>{deliveries.data.map((item) => <TableRow key={item.id}><TableCell className="whitespace-nowrap">{formatDateTime(item.created_at)}</TableCell><TableCell>{item.project_name}</TableCell><TableCell className="font-medium">{item.rule_name}</TableCell><TableCell>{riskLabels[item.business_risk_level]}</TableCell><TableCell>{item.channel === "TELEGRAM" ? "Telegram" : "Kênh thông báo"}</TableCell><TableCell>{item.recipient_name}</TableCell><TableCell><Badge variant={item.status === "SENT" ? "success" : item.status === "FAILED" ? "destructive" : "warning"}>{deliveryLabels[item.status]}</Badge></TableCell><TableCell>{item.reason ? (reasonLabels[item.reason] ?? "Lỗi gửi thông báo") : "—"}</TableCell><TableCell>{item.attempt_count}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={BellRing} title={deliveries.isError ? "Không thể tải lịch sử thông báo" : "Chưa có thông báo"} description={deliveries.isError ? "Vui lòng kiểm tra kết nối Backend." : "Các lần gửi từ sự cố vận hành sẽ xuất hiện tại đây."} />}</TabsContent>
    <TabsContent value="audit">{audit.data?.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Thời gian</TableHead><TableHead>Hành động</TableHead><TableHead>Đối tượng</TableHead><TableHead>Người thực hiện</TableHead><TableHead>Chi tiết</TableHead></TableRow></TableHeader><TableBody>{audit.data.map((log) => <TableRow key={log.id}><TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(log.created_at)}</TableCell><TableCell className="font-medium">{auditActionLabels[log.action] ?? "Thao tác hệ thống"}</TableCell><TableCell>{auditEntityLabels[log.target.type] ?? "Đối tượng"}: {log.target.display_name}</TableCell><TableCell>{log.actor.full_name}</TableCell><TableCell className="max-w-md text-sm text-muted-foreground">{formatAuditDetail(log)}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={BookOpenCheck} title="Chưa có nhật ký" description="Các thao tác thay đổi dữ liệu sẽ được ghi nhận tại đây." />}</TabsContent>
  </Tabs></div>
}
