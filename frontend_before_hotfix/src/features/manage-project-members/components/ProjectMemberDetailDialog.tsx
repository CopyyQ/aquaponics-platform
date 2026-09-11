import type { ProjectMember } from "@/entities/project-member/model/types"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/shared/ui/dialog"

export function ProjectMemberDetailDialog({ member, onOpenChange }: { member: ProjectMember | null; onOpenChange: (open: boolean) => void }) {
  return <Dialog open={Boolean(member)} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Thông tin thành viên</DialogTitle><DialogDescription>Thông tin được phép xem trong phạm vi Project.</DialogDescription></DialogHeader>{member ? <dl className="grid gap-4 sm:grid-cols-2"><div><dt className="text-sm text-muted-foreground">Họ tên</dt><dd className="font-medium">{member.full_name}</dd></div><div><dt className="text-sm text-muted-foreground">Username</dt><dd>@{member.username}</dd></div><div><dt className="text-sm text-muted-foreground">Email</dt><dd>{member.email}</dd></div><div><dt className="text-sm text-muted-foreground">Số điện thoại</dt><dd>{member.phone_number}</dd></div></dl> : null}</DialogContent></Dialog>
}
