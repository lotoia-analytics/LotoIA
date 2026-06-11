export type PlanId =
  | "basico"
  | "plus"
  | "avancado"
  | "pro"
  | "master"
  | "elite";

export type Plan = {
  id: PlanId;
  name: string;
  price: number;
  formats: string;
  formatoMax: number;
};

export const OFFICIAL_PLAN_IDS: PlanId[] = [
  "basico",
  "plus",
  "avancado",
  "pro",
  "master",
  "elite",
];

export const PLANS: Plan[] = [
  {
    id: "basico",
    name: "Básico",
    price: 15.99,
    formats: "15D",
    formatoMax: 15,
  },
  {
    id: "plus",
    name: "Plus",
    price: 29.99,
    formats: "15D + 16D",
    formatoMax: 16,
  },
  {
    id: "avancado",
    name: "Avançado",
    price: 39.99,
    formats: "15D + 17D",
    formatoMax: 17,
  },
  {
    id: "pro",
    name: "Pro",
    price: 49.99,
    formats: "15D + 18D",
    formatoMax: 18,
  },
  {
    id: "master",
    name: "Master",
    price: 59.99,
    formats: "15D + 19D",
    formatoMax: 19,
  },
  {
    id: "elite",
    name: "Elite",
    price: 69.99,
    formats: "15D + 20D",
    formatoMax: 20,
  },
];

export function getPlanById(planId: string): Plan | undefined {
  return PLANS.find((plan) => plan.id === planId);
}

export function isOfficialPlan(planId: string): planId is PlanId {
  return OFFICIAL_PLAN_IDS.includes(planId as PlanId);
}
