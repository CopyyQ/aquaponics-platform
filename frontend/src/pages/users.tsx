import { useQuery } from "@tanstack/react-query"
import { errorMessage } from "@/api/client"
import { listUsers } from "@/api/resources"

export function UsersPage() {
  const users = useQuery({ queryKey: ["users"], queryFn: listUsers })
  return <section className="space-y-5"><h1 className="text-3xl font-bold">Người dùng và RBAC</h1>{users.isError && <p className="text-destructive">{errorMessage(users.error)}</p>}<div className="overflow-auto rounded-xl border bg-card"><table className="w-full text-left"><thead><tr className="border-b"><th className="p-3">Họ tên</th><th className="p-3">Tên đăng nhập</th><th className="p-3">Vai trò</th><th className="p-3">Trạng thái</th></tr></thead><tbody>{users.data?.map((user) => <tr className="border-b" key={user.id}><td className="p-3">{user.full_name}</td><td className="p-3">{user.username}</td><td className="p-3">{user.role_name ?? user.role_code ?? "Chưa gán"}</td><td className="p-3">{user.status}</td></tr>)}</tbody></table></div></section>
}
