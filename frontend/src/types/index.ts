export type { components, paths } from './api.d.ts';
export * from './domain';

import type { components } from './api.d.ts';

export type UserProfile = components['schemas']['UserProfile'];
export type PromiseSummary = components['schemas']['PromiseSummary'];
export type PromiseDetail = components['schemas']['PromiseDetail'];
export type TimelineEvent = components['schemas']['TimelineEvent'];
export type BankCredit = components['schemas']['BankCredit'];
export type DashboardSummary = components['schemas']['DashboardSummary'];
export type EscalationNextStep = components['schemas']['EscalationNextStep'];
export type EscalationDraft = components['schemas']['EscalationDraft'];
export type MerchantRecord = components['schemas']['MerchantRecord'];
export type Job = components['schemas']['Job'];
export type HealthStatus = components['schemas']['HealthStatus'];
export type DemoSimulateResult = components['schemas']['DemoSimulateResult'];
export type VerifyResult = components['schemas']['VerifyResult'];
