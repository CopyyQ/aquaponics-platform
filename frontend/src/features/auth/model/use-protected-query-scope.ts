import { useAuthStore } from "@/features/auth/model/auth-store"

export function useProtectedQueryScope() {
  const user = useAuthStore((state) => state.user)
  const active = user?.status === "ACTIVE" && user.is_deleted === false && user.deleted_at === null
  return {
    active,
    queryScope: [user?.id, user?.token_version] as const,
  }
}
