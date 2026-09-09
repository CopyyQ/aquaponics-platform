import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { UserPlus, Users, UserMinus } from "lucide-react"
import { useParams } from "react-router-dom"
import { addMember, listMembers, queryKeys, removeMember, updateMember } from "@/api/resources"
import type { MemberRole } from "@/api/contracts"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { errorMessage } from "@/api/client"

export function MembersPage() {
  const systemId = Number(useParams().systemId); const { can } = useAuth(); const client = useQueryClient(); const [userId, setUserId] = useState("")
  const members = useQuery({ queryKey: queryKeys.members(systemId), queryFn: () => listMembers(systemId) })
  const refresh = () => void client.invalidateQueries({ queryKey: queryKeys.members(systemId) })
  const add = useMutation({ mutationFn: () => addMember(systemId, { user_id: Number(userId), role: "VIEWER" }), onSuccess: () => { setUserId(""); refresh() } })
  const update = useMutation({ mutationFn: ({ id, role }: { id: number; role: MemberRole }) => updateMember(systemId, id, { role }), onSuccess: refresh })
  const remove = useMutation({ mutationFn: (id: number) => removeMember(systemId, id), onSuccess: refresh })
  if (members.isLoading) return <Skeleton className="h-80" />
  if (members.isError) return <EmptyState icon={Users} title="Không thể tải thành viên" description={errorMessage(members.error)} />
  return <div className="space-y-5"><div><h2 className="text-xl font-semibold">Thành viên hệ thống</h2><p className="text-sm text-muted-foreground">Quyền thành viên được backend kiểm tra theo từng hệ thống.</p></div>{can("aquaponics_systems.manage_members") ? <Card><CardHeader><CardTitle className="text-base">Thêm thành viên</CardTitle></CardHeader><CardContent className="flex flex-wrap gap-2"><Input className="w-56" type="number" min="1" placeholder="User ID" value={userId} onChange={(event) => setUserId(event.target.value)} /><Button onClick={() => add.mutate()} disabled={!userId || add.isPending}><UserPlus />Thêm</Button></CardContent></Card> : null}{members.data?.length ? <Card><CardContent className="divide-y p-0">{members.data.map((member) => <div className="flex flex-wrap items-center justify-between gap-3 p-4" key={member.id}><div><p className="font-medium">{member.name}</p><p className="text-xs text-muted-foreground">User #{member.user_id} · tham gia {new Date(member.joined_at).toLocaleDateString("vi-VN")}</p></div><div className="flex items-center gap-2"><StatusBadge value={member.role} />{can("aquaponics_systems.manage_members") ? <><select aria-label={`Vai trò của ${member.name}`} className="h-9 rounded-md border bg-background px-2 text-sm" value={member.role} onChange={(event) => update.mutate({ id: member.user_id, role: event.target.value as MemberRole })}><option value="VIEWER">VIEWER</option><option value="TECHNICIAN">TECHNICIAN</option><option value="OWNER">OWNER</option></select><Button aria-label={`Xoá ${member.name}`} size="icon" variant="ghost" onClick={() => remove.mutate(member.user_id)}><UserMinus /></Button></> : null}</div></div>)}</CardContent></Card> : <EmptyState icon={Users} title="Chưa có thành viên" description="Thêm thành viên bằng User ID khi bạn có quyền quản lý." />}</div>
}
