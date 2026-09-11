import { useId, useState } from "react"

import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Label } from "@/shared/ui/label"
import { Textarea } from "@/shared/ui/textarea"

interface ResolveAlertDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  conditionActive: boolean
  currentValue: number | null
  lowerThreshold?: number | null
  upperThreshold?: number | null
  actorName?: string | null
  pending: boolean
  onConfirm: (resolutionNote: string) => void
}

export function ResolveAlertDialog({
  open,
  onOpenChange,
  conditionActive,
  currentValue,
  lowerThreshold,
  upperThreshold,
  actorName,
  pending,
  onConfirm,
}: ResolveAlertDialogProps) {
  const [note, setNote] = useState("")
  const noteId = useId()
  const helpId = `${noteId}-help`
  const valid = note.trim().length >= 3
  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setNote("")
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xác nhận cảnh báo đã được khắc phục?</DialogTitle>
          <DialogDescription>
            Thao tác này xác nhận rằng sự cố đã được người vận hành kiểm tra và xử lý.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {conditionActive ? (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm" role="alert">
              <p className="font-medium text-destructive">Giá trị hiện tại vẫn đang nằm ngoài ngưỡng cảnh báo.</p>
              <p className="mt-1 text-muted-foreground">
                Giá trị hiện tại: {currentValue ?? "—"}. Ngưỡng: {lowerThreshold ?? "—"} – {upperThreshold ?? "—"}.
                Hãy chờ giá trị trở về bình thường trước khi xác nhận.
              </p>
            </div>
          ) : null}
          <p className="text-sm">Người xác nhận: <strong>{actorName || "Tài khoản đang đăng nhập"}</strong></p>
          <div className="space-y-2">
            <Label htmlFor={noteId}>Ghi chú khắc phục</Label>
            <Textarea
              id={noteId}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              required
              aria-invalid={note.length > 0 && !valid}
              aria-describedby={helpId}
              placeholder="Mô tả việc kiểm tra và xử lý đã thực hiện"
            />
            <p id={helpId} className="text-xs text-muted-foreground">Bắt buộc, ít nhất 3 ký tự.</p>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>Hủy</Button>
          <Button
            type="button"
            disabled={conditionActive || !valid || pending}
            onClick={() => onConfirm(note.trim())}
          >
            {pending ? "Đang xác nhận…" : "Xác nhận đã khắc phục"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
