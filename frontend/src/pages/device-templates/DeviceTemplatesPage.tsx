import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Gauge,
  Power,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";

import { actuatorModelApi } from "@/entities/actuator-model/api/actuator-model-api";
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api";
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { ActuatorModelDialog } from "@/features/manage-device-templates/components/ActuatorModelDialog";
import { DeviceTemplateCard } from "@/features/manage-device-templates/components/DeviceTemplateCard";
import { DeviceTemplateDialog } from "@/features/manage-device-templates/components/DeviceTemplateDialog";
import { SensorModelDialog } from "@/features/manage-device-templates/components/SensorModelDialog";
import { formatResourceLoadError } from "@/shared/api/backend-error";
import { queryKeys } from "@/shared/api/query-keys";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Input } from "@/shared/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { Skeleton } from "@/shared/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";

type AvailabilityFilter = "ALL" | "ACTIVE" | "INACTIVE";
type CatalogTab = "devices" | "sensors" | "actuators";

function CatalogError({
  title,
  description,
  onRetry,
}: {
  title: string;
  description: string;
  onRetry: () => void;
}) {
  return (
    <EmptyState
      icon={Boxes}
      title={title}
      description={description}
      action={
        <Button variant="outline" onClick={onRetry}>
          Thử lại
        </Button>
      }
    />
  );
}

export function DeviceTemplatesPage() {
  const [search, setSearch] = useState("");
  const [queryText, setQueryText] = useState("");
  const [availability, setAvailability] = useState<AvailabilityFilter>("ALL");
  const [activeTab, setActiveTab] = useState<CatalogTab>("devices");
  const { active, queryScope } = useProtectedQueryScope();

  useEffect(() => {
    const timer = window.setTimeout(() => setQueryText(search.trim()), 275);
    return () => window.clearTimeout(timer);
  }, [search]);

  const templates = useQuery({
    queryKey: queryKeys.deviceTemplates.list(
      ...queryScope,
      queryText,
      availability,
      1,
    ),
    queryFn: () => deviceTemplateApi.list(queryText, availability),
    placeholderData: keepPreviousData,
    enabled: active,
    staleTime: 30_000,
  });
  const sensorModels = useQuery({
    queryKey: queryKeys.sensorModels.list(queryScope),
    queryFn: sensorModelApi.list,
    enabled: active,
    staleTime: 30_000,
  });
  const actuatorModels = useQuery({
    queryKey: queryKeys.actuatorModels.list(queryScope),
    queryFn: actuatorModelApi.list,
    enabled: active,
    staleTime: 30_000,
  });

  const hasFilters = queryText.length > 0 || availability !== "ALL";
  const activeAction =
    activeTab === "devices" ? (
      <DeviceTemplateDialog />
    ) : activeTab === "sensors" ? (
      <SensorModelDialog />
    ) : (
      <ActuatorModelDialog />
    );

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">
            Danh mục thiết bị
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Quản lý mẫu thiết bị, mẫu cảm biến và mẫu cơ cấu chấp hành.
          </p>
        </div>
        <div className="flex w-full shrink-0 sm:w-auto [&_button]:w-full sm:[&_button]:w-auto">
          {activeAction}
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as CatalogTab)}
      >
        <div className="overflow-x-auto">
          <TabsList className="inline-flex min-w-max">
            <TabsTrigger value="devices">Mẫu thiết bị</TabsTrigger>
            <TabsTrigger value="sensors">Mẫu cảm biến</TabsTrigger>
            <TabsTrigger value="actuators">Mẫu cơ cấu chấp hành</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="devices" className="flex flex-col gap-4">
          <Card className="overflow-hidden">
            <CardHeader>
              <div className="flex flex-col gap-1">
                <div>
                  <CardTitle>Mẫu thiết bị</CardTitle>
                  <CardDescription>
                    Thiết bị và mapping Sensor/Actuator Model dùng chung.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <div className="flex flex-col gap-3 border-y p-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative min-w-0 flex-1 sm:max-w-sm">
                  <Search
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Tìm mã hoặc tên mẫu thiết bị..."
                    aria-label="Tìm mẫu thiết bị"
                    className="pl-9 pr-9"
                  />
                  {search ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="Xóa từ khóa"
                      className="absolute right-0 top-0"
                      onClick={() => setSearch("")}
                    >
                      <X aria-hidden="true" />
                    </Button>
                  ) : null}
                </div>
                <Select
                  value={availability}
                  onValueChange={(value) =>
                    setAvailability(value as AvailabilityFilter)
                  }
                >
                  <SelectTrigger
                    className="w-full sm:w-[200px]"
                    aria-label="Lọc trạng thái mẫu"
                  >
                    <SlidersHorizontal aria-hidden="true" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="ALL">Tất cả mẫu</SelectItem>
                      <SelectItem value="ACTIVE">Đang khả dụng</SelectItem>
                      <SelectItem value="INACTIVE">Tạm ẩn</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                {hasFilters ? (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setSearch("");
                      setQueryText("");
                      setAvailability("ALL");
                    }}
                  >
                    Xóa lọc
                  </Button>
                ) : null}
              </div>
              <div className="shrink-0 text-sm text-muted-foreground">
                {templates.data?.total ?? 0} kết quả
              </div>
            </div>
            <CardContent className="p-4 sm:p-6">
              {templates.isLoading ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  <Skeleton className="h-80" />
                  <Skeleton className="h-80" />
                </div>
              ) : templates.isError ? (
                <CatalogError
                  title="Không thể tải danh sách mẫu thiết bị"
                  description={formatResourceLoadError(
                    templates.error,
                    "danh sách mẫu thiết bị",
                  )}
                  onRetry={() => void templates.refetch()}
                />
              ) : templates.data?.items.length ? (
                <div className="grid items-start gap-4 lg:grid-cols-2">
                  {templates.data.items.map((template) => (
                    <DeviceTemplateCard key={template.id} template={template} />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={Boxes}
                  title={
                    hasFilters
                      ? "Không tìm thấy mẫu thiết bị phù hợp"
                      : "Chưa có mẫu thiết bị"
                  }
                  description={
                    hasFilters
                      ? "Hãy thay đổi bộ lọc hoặc từ khóa."
                      : "Tạo mẫu thiết bị đầu tiên để cấu hình catalog."
                  }
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sensors">
          <Card className="overflow-hidden">
            <CardHeader className="flex flex-row items-start justify-between gap-4 border-b">
              <div>
                <CardTitle>Mẫu cảm biến</CardTitle>
                <CardDescription>
                  Danh mục mẫu cảm biến, không phải cảm biến đang vận hành thuộc thiết bị.
                </CardDescription>
              </div>
              <Badge variant="secondary">
                {sensorModels.data?.length ?? 0} mẫu
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              {sensorModels.isLoading ? (
                <div className="p-6">
                  <Skeleton className="h-64" />
                </div>
              ) : sensorModels.isError ? (
                <CatalogError
                  title="Không thể tải danh sách mẫu cảm biến"
                  description={formatResourceLoadError(
                    sensorModels.error,
                    "danh sách mẫu cảm biến",
                  )}
                  onRetry={() => void sensorModels.refetch()}
                />
              ) : sensorModels.data?.length ? (
                <div className="w-full overflow-x-auto">
                  <table className="hidden min-w-[900px] w-full text-sm md:table">
                    <thead className="bg-muted/40 text-left">
                      <tr>
                        <th className="p-3">Tên mẫu</th>
                        <th className="p-3">Đại lượng đo</th>
                        <th className="p-3">Đơn vị</th>
                        <th className="p-3">Kiểu dữ liệu</th>
                        <th className="p-3">Trạng thái</th>
                        <th className="p-3">Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sensorModels.data.map((model) => (
                        <tr key={model.id} className="border-t">
                          <td className="p-3 font-medium">{model.name}</td>
                          <td className="p-3">{model.name}</td>
                          <td className="p-3">{model.unit}</td>
                          <td className="p-3">{model.value_type}</td>
                          <td className="p-3">
                            <Badge
                              variant={
                                model.is_active ? "success" : "secondary"
                              }
                            >
                              {model.is_active ? "Khả dụng" : "Tạm ẩn"}
                            </Badge>
                          </td>
                          <td className="p-3 text-right">—</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState
                  icon={Gauge}
                  title="Chưa có mẫu cảm biến"
                  description="Catalog mẫu cảm biến hiện đang trống."
                />
              )}
              {sensorModels.data?.length ? (
                <div className="grid gap-3 p-4 md:hidden">
                  {sensorModels.data.map((model) => (
                    <div key={model.id} className="rounded-lg border p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{model.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {model.code}
                          </p>
                        </div>
                        <Badge
                          variant={model.is_active ? "success" : "secondary"}
                        >
                          {model.is_active ? "Khả dụng" : "Tạm ẩn"}
                        </Badge>
                      </div>
                      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <dt className="text-muted-foreground">Đại lượng</dt>
                          <dd>{model.name}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Đơn vị</dt>
                          <dd>{model.unit}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">
                            Kiểu dữ liệu
                          </dt>
                          <dd>{model.value_type}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Thao tác</dt>
                          <dd>—</dd>
                        </div>
                      </dl>
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="actuators">
          <Card className="overflow-hidden">
            <CardHeader className="flex flex-col gap-4 border-b sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle>Mẫu cơ cấu chấp hành</CardTitle>
                <CardDescription>
                  Cấu hình các loại cơ cấu chấp hành, trạng thái mặc định và khả năng giám sát điện áp/dòng điện khi gắn vào thiết bị.
                </CardDescription>
              </div>
              <Badge variant="secondary">
                {actuatorModels.data?.length ?? 0} mẫu
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              {actuatorModels.isLoading ? (
                <div className="p-6">
                  <Skeleton className="h-64" />
                </div>
              ) : actuatorModels.isError ? (
                <CatalogError
                  title="Không thể tải danh sách mẫu cơ cấu chấp hành"
                  description={formatResourceLoadError(
                    actuatorModels.error,
                    "danh sách mẫu cơ cấu chấp hành",
                  )}
                  onRetry={() => void actuatorModels.refetch()}
                />
              ) : actuatorModels.data?.length ? (
                <>
                  <div className="w-full overflow-x-auto">
                    <table className="hidden w-full text-sm lg:table">
                      <thead className="bg-muted/40 text-left">
                        <tr>
                          <th className="p-3">Mẫu cơ cấu chấp hành</th>
                          <th className="p-3">Kiểu điều khiển</th>
                          <th className="p-3">Trạng thái mặc định</th>
                          <th className="p-3">Giám sát điện</th>
                          <th className="p-3">Trạng thái</th>
                          <th className="p-3 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {actuatorModels.data.map((model) => (
                          <tr key={model.id} className="border-t">
                            <td className="p-3">
                              <p className="font-medium">{model.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {model.code}
                              </p>
                            </td>
                            <td className="p-3">{model.data_type === "BOOLEAN" ? "Bật/Tắt" : model.data_type}</td>
                            <td className="p-3">
                              {model.default_state ? "Bật" : "Tắt"}
                            </td>
                            <td className="p-3"><div className="flex flex-wrap gap-1">{model.feedbacks.filter((feedback) => feedback.is_enabled).map((feedback) => <Badge key={feedback.id} variant="secondary">{feedback.feedback_role === "SUPPLY_VOLTAGE" ? "Điện áp" : "Dòng điện"}</Badge>)}{!model.feedbacks.some((feedback) => feedback.is_enabled) ? <span className="text-muted-foreground">Không hỗ trợ</span> : null}</div></td>
                            <td className="p-3">
                              <Badge
                                variant={
                                  model.is_active ? "success" : "secondary"
                                }
                              >
                                {model.is_active
                                  ? "Đang sử dụng"
                                  : "Đã vô hiệu hóa"}
                              </Badge>
                            </td>
                            <td className="p-3 text-right"><ActuatorModelDialog model={model} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="grid gap-3 p-4 lg:hidden">
                    {actuatorModels.data.map((model) => (
                      <article key={model.id} className="rounded-lg border p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="font-medium">{model.name}</h3>
                            <p className="text-xs text-muted-foreground">
                              {model.code}
                            </p>
                          </div>
                          <Badge
                            variant={model.is_active ? "success" : "secondary"}
                          >
                            {model.is_active
                              ? "Đang sử dụng"
                              : "Đã vô hiệu hóa"}
                          </Badge>
                        </div>
                        <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <dt className="text-muted-foreground">
                              Kiểu điều khiển
                            </dt>
                            <dd>Bật/Tắt</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Mặc định</dt>
                            <dd>{model.default_state ? "Bật" : "Tắt"}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Giám sát điện</dt>
                            <dd>{model.feedbacks.filter((feedback) => feedback.is_enabled).map((feedback) => feedback.feedback_role === "SUPPLY_VOLTAGE" ? "Điện áp" : "Dòng điện").join(", ") || "Không hỗ trợ"}</dd>
                          </div>
                        </dl>
                        <p className="mt-3 text-sm text-muted-foreground">
                          {model.description || "—"}
                        </p>
                        <div className="mt-3 text-right text-sm"><ActuatorModelDialog model={model} /></div>
                      </article>
                    ))}
                  </div>
                </>
              ) : (
                <EmptyState
                  icon={Power}
                  title="Chưa có mẫu cơ cấu chấp hành"
                  description="Tạo mẫu cơ cấu chấp hành trước khi cấu hình cho mẫu thiết bị."
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
