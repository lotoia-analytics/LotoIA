import { Logo } from "@/components/Logo";

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-4 text-sm leading-relaxed text-muted">
        <Logo href="" className="opacity-90" />
        <p>
          LotoIA é uma plataforma de análise estatística. Resultados passados não garantem
          resultados futuros. Jogue com responsabilidade.
        </p>
        <p className="text-xs">© {new Date().getFullYear()} LotoIA. Todos os direitos reservados.</p>
      </div>
    </footer>
  );
}
