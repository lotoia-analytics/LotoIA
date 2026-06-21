import { PLANS, type PlanId } from "@/lib/plans";

type PlansProps = {
  onSelectPlan: (planId: PlanId) => void;
};

export function Plans({ onSelectPlan }: PlansProps) {
  const plan = PLANS[0];

  return (
    <section id="planos" className="px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">Plano LotoIA</h2>
          <p className="mt-3 text-muted">
            Um único plano: 7 dias iniciais só em 15D e, depois, 15D + 20D por 12 meses — até 30
            jogos por dia no WhatsApp.
          </p>
        </div>
        <div className="mx-auto max-w-xl">
          <article className="flex flex-col rounded-2xl border border-accent/60 bg-gradient-to-b from-accent/10 to-primary/80 p-6 shadow-card">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-xl font-semibold text-white">{plan.name}</h3>
              <span className="rounded-full bg-accent/20 px-3 py-1 text-xs font-semibold text-accent">
                Plano único
              </span>
            </div>
            <p className="text-3xl font-bold text-white">
              R$ {plan.price.toFixed(2).replace(".", ",")}
            </p>
            <p className="mt-2 text-sm text-muted">Formatos: {plan.formats}</p>
            <p className="mt-1 text-sm text-muted">
              7 dias iniciais (15D) + 12 meses (15D + 20D) · até {plan.dailyGames} jogos/dia
            </p>
            <button
              type="button"
              onClick={() => onSelectPlan(plan.id)}
              className="mt-6 rounded-xl border border-accent/40 bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#3f7be0]"
            >
              Assinar
            </button>
          </article>
        </div>
      </div>
    </section>
  );
}
