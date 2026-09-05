import { z } from "zod"

const usernamePattern = /^[A-Za-z0-9._-]+$/
const phonePattern = /^\+?[0-9]{8,15}$/

export const createAccountSchema = z.object({
  username: z.string().trim().min(3, "Tên đăng nhập tối thiểu 3 ký tự").max(100, "Tên đăng nhập tối đa 100 ký tự").regex(usernamePattern, "Chỉ dùng chữ, số, dấu chấm, gạch dưới hoặc gạch ngang"),
  full_name: z.string().trim().min(2, "Họ và tên tối thiểu 2 ký tự").max(255, "Họ và tên tối đa 255 ký tự"),
  email: z.string().trim().toLowerCase().email("Email không đúng định dạng"),
  phone_number: z.string().trim().regex(phonePattern, "Số điện thoại gồm 8–15 chữ số và có thể bắt đầu bằng dấu +"),
  address: z.string().trim().max(2000, "Địa chỉ quá dài"),
  system_role: z.enum(["ADMIN", "OWNER", "VIEWER"]),
  status: z.enum(["ACTIVE", "DISABLED", "LOCKED"]),
  password: z.string().min(8, "Mật khẩu tối thiểu 8 ký tự").max(128, "Mật khẩu tối đa 128 ký tự"),
  confirm_password: z.string().min(8, "Vui lòng xác nhận mật khẩu").max(128, "Mật khẩu tối đa 128 ký tự"),
  must_change_password: z.boolean(),
}).refine((value) => value.password === value.confirm_password, {
  message: "Mật khẩu xác nhận không trùng khớp",
  path: ["confirm_password"],
})

export type CreateAccountValues = z.infer<typeof createAccountSchema>
