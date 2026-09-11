import type { SensorModel } from "@/entities/sensor-model/model/types"

export function getAvailableSensorModels(
  models: SensorModel[],
  existingModelIds: ReadonlySet<number>,
  search: string,
): SensorModel[] {
  const keyword = search.trim().toLocaleLowerCase("vi")
  return models.filter((model) =>
    model.is_active
    && !existingModelIds.has(model.id)
    && (
      !keyword
      || `${model.code} ${model.name} ${model.unit}`.toLocaleLowerCase("vi").includes(keyword)
    )
  )
}
