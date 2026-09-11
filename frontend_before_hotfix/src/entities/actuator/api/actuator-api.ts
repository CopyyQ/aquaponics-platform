import { httpClient } from "@/shared/api/http-client";
import type { Actuator, ActuatorFeedbackBinding, ActuatorFeedbackRole, FeedbackSensorOption } from "@/entities/actuator/model/types";

export interface ActuatorCreateInput {
  actuator_model_id: number;
  location?: string | null;
  notes?: string | null;
}

export interface ActuatorUpdateInput {
  location?: string | null;
  notes?: string | null;
}

export interface ActuatorCommand {
  command_id: number;
  actuator_id: number;
  desired_state: boolean;
  reported_state: boolean | null;
  status: "PENDING" | "ACKNOWLEDGED" | "TIMEOUT" | "FAILED" | string;
  requested_at: string;
}

const base = (projectId: number, deviceId: number) =>
  `/projects/${projectId}/devices/${deviceId}/actuators`;

export const actuatorApi = {
  list: async (projectId: number, deviceId: number, includeDisabled = false) =>
    (
      await httpClient.get<Actuator[]>(base(projectId, deviceId), {
        params: { include_disabled: includeDisabled },
      })
    ).data,
  create: async (
    projectId: number,
    deviceId: number,
    payload: ActuatorCreateInput,
  ) =>
    (await httpClient.post<Actuator>(base(projectId, deviceId), payload)).data,
  update: async (
    projectId: number,
    deviceId: number,
    actuatorId: number,
    payload: ActuatorUpdateInput,
  ) =>
    (
      await httpClient.patch<Actuator>(
        `${base(projectId, deviceId)}/${actuatorId}`,
        payload,
      )
    ).data,
  remove: async (projectId: number, deviceId: number, actuatorId: number) => {
    await httpClient.delete(`${base(projectId, deviceId)}/${actuatorId}`);
  },
  disable: async (
    projectId: number,
    deviceId: number,
    actuatorId: number,
    reason: string,
  ) => {
    await httpClient.post(
      `${base(projectId, deviceId)}/${actuatorId}/disable`,
      { reason },
    );
  },
  activate: async (projectId: number, deviceId: number, actuatorId: number) => {
    await httpClient.post(
      `${base(projectId, deviceId)}/${actuatorId}/activate`,
    );
  },
  command: async (
    projectId: number,
    deviceId: number,
    actuatorId: number,
    desiredState: boolean,
  ) =>
    (
      await httpClient.post<ActuatorCommand>(
        `${base(projectId, deviceId)}/${actuatorId}/commands`,
        { desired_state: desiredState },
      )
    ).data,
  getFeedbackBinding: async (projectId: number, deviceId: number, actuatorId: number, feedbackRole: ActuatorFeedbackRole = "RUNNING_CURRENT") =>
    (await httpClient.get<ActuatorFeedbackBinding | null>(`${base(projectId, deviceId)}/${actuatorId}/feedback-binding`, { params: { feedback_role: feedbackRole } })).data,
  listFeedbackSensors: async (projectId: number, deviceId: number, actuatorId: number, feedbackRole: ActuatorFeedbackRole = "RUNNING_CURRENT") =>
    (await httpClient.get<FeedbackSensorOption[]>(`${base(projectId, deviceId)}/${actuatorId}/feedback-sensors`, { params: { feedback_role: feedbackRole } })).data,
  setFeedbackBinding: async (projectId: number, deviceId: number, actuatorId: number, payload: { sensor_id: number; feedback_role: ActuatorFeedbackRole; value_key: string; lower_threshold: number | null; upper_threshold: number | null }) =>
    (await httpClient.put<ActuatorFeedbackBinding>(`${base(projectId, deviceId)}/${actuatorId}/feedback-binding`, payload)).data,
  removeFeedbackBinding: async (projectId: number, deviceId: number, actuatorId: number, feedbackRole: ActuatorFeedbackRole = "RUNNING_CURRENT") => {
    await httpClient.delete(`${base(projectId, deviceId)}/${actuatorId}/feedback-binding`, { params: { feedback_role: feedbackRole } });
  },
};
