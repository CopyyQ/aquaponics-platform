import { useState } from "react"
import axios from "axios"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import {
  AlertCircle,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  UserRound,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { useAuthStore } from "@/features/auth/model/auth-store"

const loginSchema = z.object({
  username: z
    .string()
    .trim()
    .min(1, "Vui lòng nhập tên đăng nhập")
    .max(100, "Tên đăng nhập không được vượt quá 100 ký tự"),

  // Form đăng nhập không áp chính sách độ mạnh mật khẩu.
  // Chỉ kiểm tra người dùng đã nhập mật khẩu.
  password: z
    .string()
    .min(1, "Vui lòng nhập mật khẩu")
    .max(256, "Mật khẩu không hợp lệ"),
})

type LoginFormValues = z.infer<typeof loginSchema>

type ApiErrorData = {
  code?: string
  message?: string
  detail?:
    | string
    | {
        code?: string
        message?: string
        detail?: string
      }
}

function getLoginError(error: unknown): string {
  if (!axios.isAxiosError<ApiErrorData>(error) || !error.response) {
    return "Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối và thử lại."
  }

  const { status, data } = error.response

  const nestedDetail =
    typeof data?.detail === "object" ? data.detail : undefined

  const code = data?.code ?? nestedDetail?.code

  switch (code) {
    case "ACCOUNT_DISABLED":
    case "ACCOUNT_INACTIVE":
      return "Tài khoản hiện không hoạt động. Vui lòng liên hệ Quản trị viên."

    case "ACCOUNT_LOCKED":
      return "Tài khoản đang bị khóa. Vui lòng liên hệ Quản trị viên."

    case "ACCOUNT_DELETED":
      return "Tài khoản không còn khả dụng."

    case "TOKEN_REVOKED":
      return "Phiên đăng nhập đã hết hiệu lực. Vui lòng đăng nhập lại."

    default:
      break
  }

  if (status === 401) {
    return "Tên đăng nhập hoặc mật khẩu không chính xác."
  }

  if (status === 403) {
    return "Tài khoản không được phép truy cập hệ thống."
  }

  if (status === 422) {
    return "Thông tin đăng nhập chưa hợp lệ."
  }

  if (status === 429) {
    return "Bạn đã đăng nhập sai quá nhiều lần. Vui lòng thử lại sau."
  }

  if (status >= 500) {
    return "Máy chủ đang gặp sự cố. Vui lòng thử lại sau."
  }

  return "Không thể đăng nhập. Vui lòng kiểm tra thông tin và thử lại."
}

export function LoginForm({
  onSuccess,
}: {
  onSuccess: () => void
}) {
  const [showPassword, setShowPassword] = useState(false)

  const login = useAuthStore((state) => state.login)

  const {
    register,
    handleSubmit,
    clearErrors,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    mode: "onSubmit",
    reValidateMode: "onChange",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const usernameRegistration = register("username")
  const passwordRegistration = register("password")

  const onSubmit = handleSubmit(async (values) => {
    clearErrors("root")

    try {
      await login(values.username.trim(), values.password)

      toast.success("Đăng nhập thành công", {
        description: "Đang chuyển đến trung tâm vận hành.",
      })

      onSuccess()
    } catch (error) {
      setError("root", {
        type: "server",
        message: getLoginError(error),
      })
    }
  })

  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={onSubmit}
      noValidate
    >
      {/* Username */}
      <div className="flex flex-col gap-2">
        <Label
          htmlFor="username"
          className="text-sm font-medium"
        >
          Tên đăng nhập
        </Label>

        <div
          className={[
            "group relative rounded-xl border bg-background",
            "transition-[border-color,box-shadow]",
            "focus-within:border-primary",
            "focus-within:ring-4 focus-within:ring-primary/10",
            errors.username
              ? "border-destructive/70"
              : "border-input",
          ].join(" ")}
        >
          <UserRound
            aria-hidden="true"
            className={[
              "pointer-events-none absolute left-3.5 top-1/2",
              "size-5 -translate-y-1/2 text-muted-foreground",
              "transition-colors group-focus-within:text-primary",
            ].join(" ")}
          />

          <Input
            {...usernameRegistration}
            id="username"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoFocus
            disabled={isSubmitting}
            placeholder="Nhập tên đăng nhập hoặc email"
            aria-invalid={Boolean(errors.username)}
            aria-describedby={
              errors.username ? "username-error" : undefined
            }
            className={[
              "h-12 rounded-xl border-0 bg-transparent",
              "pl-11 pr-4 shadow-none",
              "focus-visible:ring-0 focus-visible:ring-offset-0",
            ].join(" ")}
            onChange={(event) => {
              clearErrors("root")
              usernameRegistration.onChange(event)
            }}
          />
        </div>

        {errors.username?.message ? (
          <p
            id="username-error"
            role="alert"
            className="text-xs font-medium text-destructive"
          >
            {errors.username.message}
          </p>
        ) : null}
      </div>

      {/* Password */}
      <div className="flex flex-col gap-2">
        <Label
          htmlFor="password"
          className="text-sm font-medium"
        >
          Mật khẩu
        </Label>

        <div
          className={[
            "group relative rounded-xl border bg-background",
            "transition-[border-color,box-shadow]",
            "focus-within:border-primary",
            "focus-within:ring-4 focus-within:ring-primary/10",
            errors.password
              ? "border-destructive/70"
              : "border-input",
          ].join(" ")}
        >
          <LockKeyhole
            aria-hidden="true"
            className={[
              "pointer-events-none absolute left-3.5 top-1/2",
              "size-5 -translate-y-1/2 text-muted-foreground",
              "transition-colors group-focus-within:text-primary",
            ].join(" ")}
          />

          <Input
            {...passwordRegistration}
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            disabled={isSubmitting}
            placeholder="Nhập mật khẩu"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={
              errors.password ? "password-error" : undefined
            }
            className={[
              "h-12 rounded-xl border-0 bg-transparent",
              "pl-11 pr-12 shadow-none",
              "focus-visible:ring-0 focus-visible:ring-offset-0",
            ].join(" ")}
            onChange={(event) => {
              clearErrors("root")
              passwordRegistration.onChange(event)
            }}
          />

          <button
            type="button"
            disabled={isSubmitting}
            aria-label={
              showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"
            }
            aria-pressed={showPassword}
            className={[
              "absolute right-1.5 top-1/2 grid size-9",
              "-translate-y-1/2 place-items-center rounded-lg",
              "text-muted-foreground transition-colors",
              "hover:bg-muted hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-ring focus-visible:ring-offset-2",
              "disabled:pointer-events-none disabled:opacity-50",
            ].join(" ")}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => setShowPassword((current) => !current)}
          >
            {showPassword ? (
              <EyeOff aria-hidden="true" className="size-5" />
            ) : (
              <Eye aria-hidden="true" className="size-5" />
            )}
          </button>
        </div>

        {errors.password?.message ? (
          <p
            id="password-error"
            role="alert"
            className="text-xs font-medium text-destructive"
          >
            {errors.password.message}
          </p>
        ) : null}
      </div>

      {/* Server error */}
      {errors.root?.message ? (
        <div
          role="alert"
          aria-live="polite"
          className={[
            "flex items-start gap-3 rounded-xl",
            "border border-destructive/25",
            "bg-destructive/5 px-4 py-3",
            "text-sm text-destructive",
          ].join(" ")}
        >
          <AlertCircle
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0"
          />

          <p className="leading-5">{errors.root.message}</p>
        </div>
      ) : null}

      <Button
        type="submit"
        size="lg"
        disabled={isSubmitting}
        className={[
          "h-12 w-full rounded-xl",
          "text-base font-semibold shadow-sm",
          "transition-[transform,box-shadow]",
          "hover:shadow-md active:scale-[0.99]",
        ].join(" ")}
      >
        {isSubmitting ? (
          <>
            <LoaderCircle
              data-icon="inline-start"
              className="animate-spin"
            />
            Đang đăng nhập...
          </>
        ) : (
          <>
            <LogIn data-icon="inline-start" />
            Đăng nhập
          </>
        )}
      </Button>

      <p className="text-center text-xs leading-5 text-muted-foreground">
        Chỉ tài khoản được PLAB cấp quyền mới có thể truy cập hệ thống.
      </p>
    </form>
  )
}