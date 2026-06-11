const STEPS = [
  {
    number: "1",
    title: "Escolha seu plano",
    description: "Selecione o formato máximo e o valor mensal ideal para você.",
  },
  {
    number: "2",
    title: "Pague via PIX",
    description: "Confirmação automática após o pagamento — sem burocracia.",
  },
  {
    number: "3",
    title: "Receba seus jogos no WhatsApp",
    description: "Mande olá para o bot LotoIA e peça seus jogos estruturados.",
  },
];

export function HowItWorks() {
  return (
    <section id="como-funciona" className="px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">Como funciona</h2>
          <p className="mt-3 text-muted">
            Três passos simples para ativar sua assinatura e começar a gerar jogos.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {STEPS.map((step) => (
            <article
              key={step.number}
              className="rounded-2xl border border-white/10 bg-primary/70 p-6 shadow-card"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/15 text-sm font-bold text-accent">
                {step.number}
              </div>
              <h3 className="text-xl font-semibold text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{step.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
