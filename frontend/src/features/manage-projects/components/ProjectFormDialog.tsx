import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { projectApi } from "@/entities/project/api/project-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Textarea } from "@/shared/ui/textarea"

interface Values { code: string; name: string; location?: string; description?: string }

export function ProjectFormDialog({ userId }: { userId: number }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const { register, handleSubmit, reset } = useForm<Values>()
  const mutation = useMutation({
    mutationFn: (values: Values) => projectApi.createForUser(userId, values),
    onSuccess: async (project) => {
      queryClient.setQueryData(queryKeys.projects.list(queryScope, project.id), project)
      await invalidateQueries.projects(queryClient, queryScope, project.id, userId)
      reset()
      setOpen(false)
      toast.success(`Đã tạo Project ${project.name}`)
    },
    onError: () => toast.error("Không thể tạo Project"),
  })
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button><Plus data-icon="inline-start" />Thêm dự án</Button></DialogTrigger>
    <DialogContent>
      <DialogHeader><DialogTitle>Thêm dự án</DialogTitle><DialogDescription>Project mới sẽ thuộc khách hàng hiện tại.</DialogDescription></DialogHeader>
      <form className="flex flex-col gap-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2"><Label htmlFor="project-name">Tên Project</Label><Input id="project-name" required minLength={2} {...register("name")} /></div>
          <div className="flex flex-col gap-2"><Label htmlFor="project-code">Mã Project</Label><Input id="project-code" required pattern="[A-Z0-9_-]{3,80}" placeholder="AQUA-MEKONG-01" {...register("code")} /></div>
        </div>
        <div className="flex flex-col gap-2"><Label htmlFor="project-location">Địa điểm</Label><Input id="project-location" {...register("location")} /></div>
        <div className="flex flex-col gap-2"><Label htmlFor="project-description">Mô tả</Label><Textarea id="project-description" {...register("description")} /></div>
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>Tạo Project</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
