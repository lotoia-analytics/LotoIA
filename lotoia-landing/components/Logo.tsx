import Image from "next/image";
import Link from "next/link";

type LogoProps = {
  className?: string;
  href?: string;
};

export function Logo({ className = "", href = "/" }: LogoProps) {
  const image = (
    <Image
      src="/lotoia-logo.svg"
      alt="LotoIA"
      width={220}
      height={56}
      priority
      className={`h-10 w-auto sm:h-12 ${className}`}
    />
  );

  if (!href) {
    return image;
  }

  return (
    <Link href={href} className="inline-flex items-center" aria-label="LotoIA — início">
      {image}
    </Link>
  );
}
