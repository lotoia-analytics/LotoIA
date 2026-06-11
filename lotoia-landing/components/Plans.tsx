import { PLANS, type PlanId } from "@/lib/plans";

type PlansProps = {
  onSelectPlan: (planId: PlanId) => void;
};

export function Plans({ onSelectPlan }: PlansProps) {
  return (
    <section id="planos" className="px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">Planos</h2>
          <p className="mt-3 text-muted">
            Todos os planos incluem 30 dias de acesso e até 30 jogos por dia no WhatsApp.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {PLANS.map((plan) => {
            const featured = plan.id === "pro";
            return (
              <article
                key={plan.id}
                className={`flex flex-col rounded-2xl border p-6 shadow-card ${
                  featured
                    ? "border-accent/60 bg-gradient-to-b from-accent/10 to-primary/80"
                    : "border-white/10 bg-primary/70"
                }`}
              >
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h3 className="text-xl font-semibold text-white">{plan.name}</h3>
                  {featured ? (
                    <span className="rounded-full bg-accent/20 px-3 py-1 text-xs font-semibold text-accent">
                      Popular
                    </span>
                  ) : null}
                </div>
                <p className="text-3xl font-bold text-white">
                  R$ {plan.price.toFixed(2).replace(".", ",")}
                </p>
                <p className="mt-2 text-sm text-muted">Formatos: {plan.formats}</p>
                <p className="mt-1 text-sm text-muted">30 dias | até 30 jogos por dia</p>
                <button
                  type="button"
                  onClick={() => onSelectPlan(plan.id)}
                  className="mt-6 rounded-xl border border-accent/40 bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#3f7be0]"
                >
                  Assinar
                </button>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
