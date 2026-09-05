import { userApi } from "@/entities/user/api/user-api"

export const accountApi = {
  list: userApi.adminList,
  create: userApi.adminCreate,
  update: userApi.adminUpdate,
  setPassword: userApi.adminSetPassword,
  activate: userApi.activate,
  disable: userApi.disableAccount,
  lock: userApi.lock,
  unlock: userApi.unlock,
  softDelete: userApi.softDelete,
  restore: userApi.restore,
}
