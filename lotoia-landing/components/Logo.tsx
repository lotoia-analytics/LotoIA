import Image from "next/image";
import Link from "next/link";

type LogoProps = {
  className?: string;
  href?: string;
};

export function Logo({ className = "", href = "/" }: LogoProps) {
  const content = (
    <span className={`inline-flex items-center gap-2.5 sm:gap-3 ${className}`}>
      <Image
        src="/lotoia-icon.png"
        alt=""
        width={48}
        height={63}
        priority
        className="h-10 w-auto sm:h-12"
        aria-hidden
      />
      <span className="text-2xl font-extrabold tracking-tight sm:text-3xl">
        <span className="text-white">Loto</span>
        <span className="bg-gradient-to-r from-[#6fa8ff] to-[#b794f6] bg-clip-text text-transparent">
          IA
        </span>
      </span>
    </span>
  );

  if (!href) {
    return content;
  }

  return (
    <Link href={href} className="inline-flex items-center" aria-label="LotoIA — início">
      {content}
    </Link>
  );
}
