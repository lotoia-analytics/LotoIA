export type PlanId = "completo";

export type Plan = {
  id: PlanId;
  name: string;
  price: number;
  formats: string;
  formatoMax: number;
  trialDays: number;
  fullAccessDays: number;
  subscriptionDays: number;
  dailyGames: number;
};

export const OFFICIAL_PLAN_IDS: PlanId[] = ["completo"];

export const PLANS: Plan[] = [
  {
    id: "completo",
    name: "Completo",
    price: 99.9,
    formats: "15D (7 dias) → 15D + 20D",
    formatoMax: 20,
    trialDays: 7,
    fullAccessDays: 365,
    subscriptionDays: 372,
    dailyGames: 30,
  },
];

export function getPlanById(planId: string): Plan | undefined {
  return PLANS.find((plan) => plan.id === planId);
}

export function isOfficialPlan(planId: string): planId is PlanId {
  return OFFICIAL_PLAN_IDS.includes(planId as PlanId);
}
