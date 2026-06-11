export function Footer() {
  return (
    <footer className="border-t border-white/10 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-4 text-sm leading-relaxed text-muted">
        <p className="font-medium text-white">LotoIA</p>
        <p>
          LotoIA é uma plataforma de análise estatística. Resultados passados não garantem
          resultados futuros. Jogue com responsabilidade.
        </p>
        <p className="text-xs">© {new Date().getFullYear()} LotoIA. Todos os direitos reservados.</p>
      </div>
    </footer>
  );
}
