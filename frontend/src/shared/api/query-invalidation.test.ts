import { QueryClient } from "@tanstack/react-query"
import { describe, expect, it, vi } from "vitest"

import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"

const scope = [7, 3] as const

function trackedClient() {
  const client = new QueryClient()
  const spy = vi.spyOn(client, "invalidateQueries").mockResolvedValue()
  return { client, spy }
}

type TrackedInvalidateSpy = ReturnType<typeof trackedClient>["spy"]

function calledKeys(spy: TrackedInvalidateSpy) {
  return spy.mock.calls.map(([filters]) => filters?.queryKey)
}

function expectActiveRefetch(spy: TrackedInvalidateSpy) {
  expect(spy.mock.calls.length).toBeGreaterThan(0)
  for (const [filters] of spy.mock.calls) {
    expect(filters?.refetchType).toBe("active")
  }
}

describe("query invalidation CRUD", () => {
  it("đồng bộ CRUD tài khoản với danh sách, chi tiết, dự án và dashboard", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.users(client, scope, 11)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.users.all,
      queryKeys.users.detail(scope, 11),
      queryKeys.users.projects(scope, 11),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
      queryKeys.alerts.adminRoot,
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ CRUD dự án với owner, device, monitoring, telemetry và cảnh báo", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.projects(client, scope, 21, 11)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.projects.detail(scope, 21),
      queryKeys.users.projects(scope, 11),
      queryKeys.projects.devices(scope, 21),
      queryKeys.projects.monitoring(scope, 21),
      queryKeys.projects.telemetry(scope, 21),
      queryKeys.alerts.adminRoot,
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ bật/tắt device với mọi summary liên quan", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.devices(client, scope, 21, 31, 11)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.projects.devices(scope, 21),
      queryKeys.devices.detail(scope, 21, 31),
      queryKeys.devices.sensors(scope, 21, 31),
      queryKeys.projects.monitoring(scope, 21),
      queryKeys.projects.telemetry(scope, 21),
      queryKeys.adminOverview.all,
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ bật/tắt sensor với history, telemetry, monitoring và alert", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.sensors(client, scope, 21, 31, 41)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.devices.sensors(scope, 21, 31),
      queryKeys.sensors.detail(scope, 21, 31, 41),
      queryKeys.sensors.history(scope, 21, 31, 41),
      queryKeys.projects.devices(scope, 21),
      queryKeys.projects.monitoring(scope, 21),
      queryKeys.projects.telemetry(scope, 21),
      queryKeys.alerts.all,
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ CRUD thành viên ở cả project và user", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.projectMembers(client, scope, 21, 11)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.projects.members(scope, 21),
      queryKeys.projects.detail(scope, 21),
      queryKeys.users.projects(scope, 11),
      queryKeys.users.detail(scope, 11),
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ xử lý cảnh báo với project và admin overview", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.alerts(client, scope, 21, 51)
    expect(calledKeys(spy)).toEqual(expect.arrayContaining([
      queryKeys.alerts.all,
      queryKeys.alerts.adminRoot,
      queryKeys.alerts.adminDetail(51),
      queryKeys.projects.alerts(scope, 21),
      queryKeys.projects.monitoring(scope, 21),
      queryKeys.adminOverview.all,
    ]))
    expectActiveRefetch(spy)
  })

  it("đồng bộ CRUD mẫu thiết bị và quan hệ cảm biến", async () => {
    const { client, spy } = trackedClient()
    await invalidateQueries.deviceTemplates(client)
    expect(calledKeys(spy)).toEqual([queryKeys.deviceTemplates.all])
    expectActiveRefetch(spy)
  })

  it("đánh dấu query không mở là stale", async () => {
    const client = new QueryClient()
    const key = queryKeys.projects.monitoring(scope, 21)
    client.setQueryData(key, { total: 1 })
    await invalidateQueries.devices(client, scope, 21, 31)
    expect(client.getQueryState(key)?.isInvalidated).toBe(true)
  })

  it("chờ toàn bộ invalidation hoàn tất trước khi mutation có thể đóng dialog", async () => {
    const client = new QueryClient()
    let release: (() => void) | undefined
    const pending = new Promise<void>((resolve) => { release = resolve })
    vi.spyOn(client, "invalidateQueries").mockImplementation(() => pending)
    let settled = false
    const task = invalidateQueries.users(client, scope, 11).then(() => { settled = true })
    await Promise.resolve()
    expect(settled).toBe(false)
    release?.()
    await task
    expect(settled).toBe(true)
  })

  it("không trùng query key giữa các resource và scope", () => {
    const keys = [
      queryKeys.users.detail(scope, 1),
      queryKeys.users.projects(scope, 1),
      queryKeys.projects.detail(scope, 1),
      queryKeys.projects.devices(scope, 1),
      queryKeys.devices.detail(scope, 1, 1),
      queryKeys.devices.sensors(scope, 1, 1),
      queryKeys.sensors.detail(scope, 1, 1, 1),
      queryKeys.sensors.history(scope, 1, 1, 1),
    ].map((key) => JSON.stringify(key))
    expect(new Set(keys).size).toBe(keys.length)
  })
})
