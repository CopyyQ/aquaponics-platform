import { QueryClient } from "@tanstack/react-query"
import { isAccountAuthError } from "@/shared/api/auth-errors"

/** Shared infrastructure client; it deliberately has no dependency on the app layer. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => !isAccountAuthError(error) && failureCount < 1,
      refetchOnWindowFocus: false,
    },
  },
})
