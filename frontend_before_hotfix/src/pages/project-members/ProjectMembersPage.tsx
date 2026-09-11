import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Users, X } from "lucide-react"
import { useNavigate, useParams } from "react-router-dom"
import { projectMemberApi } from "@/entities/project-member/api/project-member-api"
import type { ProjectMember } from "@/entities/project-member/model/types"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { AddProjectMemberDialog } from "@/features/manage-project-members/components/AddProjectMemberDialog"
import { ProjectMemberDetailDialog } from "@/features/manage-project-members/components/ProjectMemberDetailDialog"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function ProjectMembersPage() {
  const projectId = Number(useParams().projectId)
  const role = useAuthStore((state) => state.user?.system_role)
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState("")
  const [queryKeyword, setQueryKeyword] = useState("")
  const [selected, setSelected] = useState<ProjectMember | null>(null)
  const { active, queryScope } = useProtectedQueryScope()
  useEffect(() => {
    const timeout = window.setTimeout(() => setQueryKeyword(keyword.trim()), 275)
    return () => window.clearTimeout(timeout)
  }, [keyword])
  const query = useQuery({
    queryKey: queryKeys.projects.members(queryScope, projectId, { q: queryKeyword, page: 1 }),
    queryFn: () => projectMemberApi.list(projectId, queryKeyword),
    enabled: active && Number.isInteger(projectId) && projectId > 0,
  })
  const openMember = (member: ProjectMember) => role === "ADMIN" ? navigate(`/admin/users/${member.user_id}`) : setSelected(member)

  return <div className="flex flex-col gap-6"><PageHeader title="Thành viên Project" description="Viewer được cấp quyền ở cấp Project, áp dụng cho mọi Device và Sensor bên trong." actions={role !== "VIEWER" ? <AddProjectMemberDialog projectId={projectId} /> : undefined} /><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div className="relative w-full sm:max-w-md"><Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="px-9" value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="Tìm theo tên, username, email hoặc số điện thoại" aria-label="Tìm thành viên" />{keyword ? <Button variant="ghost" size="icon" className="absolute right-0 top-0" aria-label="Xóa từ khóa" onClick={() => setKeyword("")}><X /></Button> : null}</div><p className="text-sm text-muted-foreground" aria-live="polite">{query.data?.total ?? 0} kết quả</p></div>{query.isLoading ? <Skeleton className="h-64" /> : query.isError ? <EmptyState icon={Users} title="Không thể tải thành viên" description="Vui lòng kiểm tra quyền truy cập và thử lại." /> : query.data?.items.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Họ tên</TableHead><TableHead>Liên hệ</TableHead><TableHead>Vai trò</TableHead><TableHead>Trạng thái</TableHead><TableHead>Ngày được thêm</TableHead><TableHead>Người thêm</TableHead></TableRow></TableHeader><TableBody>{query.data.items.map((member) => <TableRow key={member.id} role="button" tabIndex={0} className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => openMember(member)} onKeyDown={(event) => { if (event.key === "Enter") openMember(member) }}><TableCell><div className="font-medium">{member.full_name}</div><div className="text-xs text-muted-foreground">@{member.username}</div></TableCell><TableCell><div>{member.email}</div><div className="text-xs text-muted-foreground">{member.phone_number}</div></TableCell><TableCell><StatusBadge value={member.role} /></TableCell><TableCell><StatusBadge value={member.status} /></TableCell><TableCell>{formatDateTime(member.created_at)}</TableCell><TableCell>{member.created_by_name || "Hệ thống"}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={Users} title="Không tìm thấy thành viên phù hợp" description="Thử thay đổi hoặc xóa từ khóa tìm kiếm." />}<ProjectMemberDetailDialog member={selected} onOpenChange={(open) => { if (!open) setSelected(null) }} /></div>
}
