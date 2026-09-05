import { create } from "zustand"
import { queryClient } from "@/shared/api/query-client"
import { httpClient } from "@/shared/api/http-client"
import type { User } from "@/entities/user/model/types"

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  hydrate: () => Promise<void>
  logout: () => void
  clear: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("aquaponics_access_token"),
  loading: true,
  login: async (username, password) => {
    await queryClient.cancelQueries()
    queryClient.clear()
    const { data } = await httpClient.post<{ access_token: string }>("/auth/login", { username, password })
    localStorage.setItem("aquaponics_access_token", data.access_token)
    set({ token: data.access_token })
    try {
      const user = (await httpClient.get<User>("/auth/me")).data
      set({ user, loading: false })
    } catch (error) {
      localStorage.removeItem("aquaponics_access_token")
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      await queryClient.cancelQueries()
      queryClient.clear()
      set({ user: null, token: null, loading: false })
      throw error
    }
  },
  hydrate: async () => {
    if (!get().token) return set({ loading: false, user: null })
    try {
      const user = (await httpClient.get<User>("/auth/me")).data
      set({ user, loading: false })
    } catch {
      localStorage.removeItem("aquaponics_access_token")
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      await queryClient.cancelQueries()
      queryClient.clear()
      set({ user: null, token: null, loading: false })
    }
  },
  logout: () => {
    localStorage.removeItem("aquaponics_access_token")
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    sessionStorage.clear()
    queryClient.clear()
    set({ user: null, token: null, loading: false })
  },
  clear: () => set({ user: null, token: null, loading: false }),
  setUser: (user) => set({ user }),
}))
