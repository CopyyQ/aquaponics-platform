import { Navigate, useNavigate } from "react-router-dom"
import {
  Activity,
  ArrowRight,
  Droplets,
  Fish,
  Leaf,
  ShieldCheck,
  Waves,
} from "lucide-react"

import { LoginForm } from "@/features/auth/components/login-form"
import { useAuthStore } from "@/features/auth/model/auth-store"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card"

function getHomePath(role?: string) {
  return role === "ADMIN" ? "/admin/overview" : "/overview"
}

const platformFeatures = [
  {
    icon: Activity,
    title: "Giám sát thời gian thực",
    description:
      "Theo dõi chất lượng nước, thiết bị và cảm biến trong một giao diện thống nhất.",
  },
  {
    icon: ShieldCheck,
    title: "Quản lý theo dự án",
    description:
      "Dữ liệu được phân tách rõ ràng theo khách hàng, dự án và quyền truy cập.",
  },
  {
    icon: Waves,
    title: "Phát hiện rủi ro sớm",
    description:
      "Ưu tiên cảnh báo bất thường để đội vận hành phản ứng kịp thời.",
  },
]

export function LoginPage() {
  const navigate = useNavigate()

  const token = useAuthStore((state) => state.token)
  const role = useAuthStore((state) => state.user?.system_role)

  if (token) {
    return <Navigate to={getHomePath(role)} replace />
  }

  const openHome = async () => {
    await useAuthStore.getState().hydrate()
    const currentRole = useAuthStore.getState().user?.system_role

    navigate(getHomePath(currentRole), {
      replace: true,
    })
  }

  return (
    <div className="relative min-h-[100svh] overflow-hidden bg-[#f4faf7] text-slate-950">
      {/* Background decoration */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="absolute -left-40 -top-40 size-[34rem] rounded-full bg-emerald-200/35 blur-3xl" />
        <div className="absolute -bottom-56 right-[-8rem] size-[38rem] rounded-full bg-cyan-200/30 blur-3xl" />

        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(15,118,110,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(15,118,110,0.04)_1px,transparent_1px)] bg-[size:48px_48px]" />
      </div>

      <div className="relative grid min-h-[100svh] lg:grid-cols-[minmax(0,1.12fr)_minmax(430px,0.88fr)]">
        {/* Brand / landing content */}
        <section className="relative hidden overflow-hidden bg-[#073f3b] text-white lg:flex lg:flex-col">
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(52,211,153,0.22),transparent_34%),radial-gradient(circle_at_85%_85%,rgba(34,211,238,0.18),transparent_32%)]"
          />

          <div
            aria-hidden="true"
            className="absolute -right-28 top-28 size-80 rounded-full border border-white/10"
          />
          <div
            aria-hidden="true"
            className="absolute -right-12 top-44 size-52 rounded-full border border-white/10"
          />

          <div className="relative z-10 flex h-full flex-col px-10 py-9 xl:px-14 xl:py-12">
            {/* Brand */}
            <header className="flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <div className="grid size-12 place-items-center rounded-2xl bg-white text-[#08766c] shadow-lg shadow-black/10">
                  <Droplets className="size-6" aria-hidden="true" />
                </div>

                <div>
                  <div className="text-xl font-bold tracking-tight">
                    PLAB Aquaponics
                  </div>
                  <div className="text-sm text-emerald-100/70">
                    Nền tảng vận hành thông minh
                  </div>
                </div>
              </div>

              <div className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-medium text-emerald-50/80 backdrop-blur">
                Trung tâm giám sát
              </div>
            </header>

            {/* Hero */}
            <div className="my-auto grid items-center gap-12 xl:grid-cols-[minmax(0,1fr)_280px]">
              <div className="max-w-2xl">
                <h1 className="text-balance text-4xl font-semibold leading-[1.12] tracking-[-0.035em] xl:text-6xl">
                  Vận hành Aquaponics bằng dữ liệu chính xác.
                </h1>

                <p className="mt-6 max-w-xl text-lg leading-8 text-emerald-50/70">
                  Theo dõi chất lượng nước, tình trạng thiết bị và cảnh báo
                  của từng dự án trên một hệ thống quản trị tập trung do PLAB
                  phát triển.
                </p>

                <div className="mt-9 flex items-center gap-3 text-sm font-medium text-emerald-100">
                  <span className="grid size-9 place-items-center rounded-full bg-emerald-400/15">
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </span>
                  Dữ liệu rõ ràng, phản ứng nhanh, vận hành chủ động.
                </div>
              </div>

              {/* Aquaponics loop */}
              <div className="relative hidden xl:block">
                <div className="relative mx-auto aspect-square w-full max-w-[270px]">
                  <div
                    aria-hidden="true"
                    className="absolute inset-0 animate-[spin_28s_linear_infinite] rounded-full border border-dashed border-white/20"
                  />
                  <div
                    aria-hidden="true"
                    className="absolute inset-8 rounded-full border border-white/10"
                  />

                  <div className="absolute inset-[28%] grid place-items-center rounded-full bg-white text-[#08766c] shadow-2xl shadow-black/20">
                    <Droplets className="size-10" aria-hidden="true" />
                  </div>

                  <div className="absolute left-1/2 top-0 flex -translate-x-1/2 flex-col items-center gap-2">
                    <div className="grid size-14 place-items-center rounded-2xl border border-white/15 bg-white/10 backdrop-blur-md">
                      <Leaf className="size-7 text-emerald-200" />
                    </div>
                    <span className="text-xs font-medium text-emerald-100/75">
                      Cây trồng
                    </span>
                  </div>

                  <div className="absolute bottom-5 left-1 flex flex-col items-center gap-2">
                    <div className="grid size-14 place-items-center rounded-2xl border border-white/15 bg-white/10 backdrop-blur-md">
                      <Fish className="size-7 text-cyan-200" />
                    </div>
                    <span className="text-xs font-medium text-emerald-100/75">
                      Thủy sản
                    </span>
                  </div>

                  <div className="absolute bottom-5 right-1 flex flex-col items-center gap-2">
                    <div className="grid size-14 place-items-center rounded-2xl border border-white/15 bg-white/10 backdrop-blur-md">
                      <Activity className="size-7 text-amber-200" />
                    </div>
                    <span className="text-xs font-medium text-emerald-100/75">
                      Cảm biến
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature row */}
            <div className="grid grid-cols-3 border-t border-white/10">
              {platformFeatures.map((feature) => {
                const Icon = feature.icon

                return (
                  <div
                    key={feature.title}
                    className="border-r border-white/10 px-5 py-6 first:pl-0 last:border-r-0 last:pr-0"
                  >
                    <Icon
                      className="mb-4 size-5 text-emerald-300"
                      aria-hidden="true"
                    />

                    <strong className="block text-sm font-semibold text-white">
                      {feature.title}
                    </strong>

                    <p className="mt-2 text-xs leading-5 text-emerald-50/55">
                      {feature.description}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* Login section */}
        <main className="flex min-h-[100svh] flex-col">
          {/* Mobile brand */}
          <header className="flex items-center gap-3 px-6 py-6 lg:hidden">
            <div className="grid size-11 place-items-center rounded-2xl bg-[#08766c] text-white shadow-sm">
              <Droplets className="size-5" aria-hidden="true" />
            </div>

            <div>
              <div className="font-bold tracking-tight text-slate-950">
                PLAB Aquaponics
              </div>
              <div className="text-xs text-slate-500">
                Nền tảng vận hành thông minh
              </div>
            </div>
          </header>

          <div className="flex flex-1 items-center justify-center px-5 py-8 sm:px-10 lg:px-12 xl:px-20">
            <div className="w-full max-w-[440px]">
              <div className="mb-8">
                <div className="mb-6 hidden size-12 place-items-center rounded-2xl bg-[#08766c] text-white shadow-lg shadow-emerald-950/10 lg:grid">
                  <Droplets className="size-6" aria-hidden="true" />
                </div>

                <h2 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950">
                  Chào mừng trở lại
                </h2>

                <p className="mt-3 max-w-sm text-sm leading-6 text-slate-500">
                  Đăng nhập để truy cập hệ thống quản lý và giám sát các dự án
                  Aquaponics của PLAB.
                </p>
              </div>

              <Card className="border-white/70 bg-white/90 shadow-[0_24px_80px_-28px_rgba(15,118,110,0.28)] backdrop-blur-xl">
                <CardHeader className="space-y-2 pb-5">
                  <CardTitle className="text-xl font-semibold tracking-tight">
                    Đăng nhập hệ thống
                  </CardTitle>

                  <CardDescription className="leading-6">
                    Sử dụng tài khoản do Quản trị viên PLAB cấp.
                  </CardDescription>
                </CardHeader>

                <CardContent>
                  <LoginForm onSuccess={openHome} />
                </CardContent>
              </Card>

              <div className="mt-7 flex flex-col items-center justify-between gap-3 text-center text-xs text-slate-500 sm:flex-row sm:text-left">
                <span>© 2026 PLAB. Aquaponics Operations Platform.</span>

                <span className="inline-flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  Hệ thống nội bộ
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
