import { z } from "zod"

export const setPasswordSchema = z.object({
  new_password: z.string().min(8, "Mật khẩu tối thiểu 8 ký tự").max(128, "Mật khẩu tối đa 128 ký tự"),
  confirm_password: z.string().min(8, "Vui lòng xác nhận mật khẩu").max(128, "Mật khẩu tối đa 128 ký tự"),
  invalidate_sessions: z.boolean(),
  must_change_password: z.boolean(),
}).refine((value) => value.new_password === value.confirm_password, {
  message: "Mật khẩu xác nhận không trùng khớp",
  path: ["confirm_password"],
})

export type SetPasswordValues = z.infer<typeof setPasswordSchema>
