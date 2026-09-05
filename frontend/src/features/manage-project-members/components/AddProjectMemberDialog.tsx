import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { UserPlus } from "lucide-react"
import { toast } from "sonner"
import { projectMemberApi } from "@/entities/project-member/api/project-member-api"
import { userApi } from "@/entities/user/api/user-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

export function AddProjectMemberDialog({ projectId }: { projectId: number }) {
  const [open, setOpen] = useState(false)
  const [userId, setUserId] = useState<number | null>(null)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const users = useQuery({ queryKey: queryKeys.users.availableMembers(projectId), queryFn: userApi.list, enabled: open })
  const mutation = useMutation({
    mutationFn: () => projectMemberApi.add(projectId, userId!),
    onSuccess: async () => {
      await invalidateQueries.projectMembers(queryClient, queryScope, projectId, userId ?? undefined)
      setUserId(null)
      setOpen(false)
      toast.success("Đã thêm Viewer vào Project")
    },
    onError: () => toast.error("Không thể thêm thành viên"),
  })
  const viewers = users.data?.filter((user) => user.system_role === "VIEWER" && user.status === "ACTIVE") ?? []

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button><UserPlus data-icon="inline-start" />Thêm thành viên</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Thêm Viewer vào Project</DialogTitle><DialogDescription>Viewer sẽ xem được mọi Device, Sensor, Telemetry và Alert trong Project.</DialogDescription></DialogHeader>
        <div className="flex flex-col gap-2"><Label>Người dùng</Label><Select onValueChange={(value) => setUserId(Number(value))}><SelectTrigger><SelectValue placeholder="Chọn Viewer" /></SelectTrigger><SelectContent><SelectGroup>{viewers.map((user) => <SelectItem key={user.id} value={String(user.id)}>{user.full_name} (@{user.username})</SelectItem>)}</SelectGroup></SelectContent></Select></div>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button disabled={!userId || mutation.isPending} onClick={() => mutation.mutate()}>Thêm vào Project</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
