type HeroProps = {
  onCtaClick: () => void;
};

export function Hero({ onCtaClick }: HeroProps) {
  return (
    <section className="relative overflow-hidden px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pb-24 lg:pt-16">
      <div className="mx-auto max-w-6xl">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-muted">
          <span className="h-2 w-2 rounded-full bg-accent" />
          Plataforma estatística estrutural
        </div>
        <h1 className="mt-6 max-w-4xl text-4xl font-bold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
          Jogue Lotofácil com Inteligência Estatística
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted sm:text-xl">
          Análise de 3.700+ concursos oficiais.
          <br />
          Sem achismo. Sem promessas. Com evidência.
        </p>
        <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={onCtaClick}
            className="rounded-xl bg-accent px-6 py-4 text-base font-semibold text-white transition hover:bg-[#3f7be0]"
          >
            Quero meus jogos agora
          </button>
          <a
            href="#como-funciona"
            className="text-center text-sm font-medium text-muted transition hover:text-white sm:text-left"
          >
            Ver como funciona
          </a>
        </div>
      </div>
    </section>
  );
}
