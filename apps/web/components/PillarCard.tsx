import Link from "next/link";
import type { ReactNode } from "react";
import { Icon, type IconName } from "@/components/Icon";

interface PillarCardProps {
  icon: IconName;
  title: string;
  desc: string;
  href: string;
  proof: ReactNode;
  cta?: string;
}

export function PillarCard({ icon, title, desc, href, proof, cta = "Open" }: PillarCardProps) {
  return (
    <div className="pillar-card">
      <div className="pillar-card__top">
        <span className="pillar-card__icon" aria-hidden="true">
          <Icon name={icon} size={24} />
        </span>
      </div>
      <h3>{title}</h3>
      <p>{desc}</p>
      <div className="pillar-card__proof">{proof}</div>
      <Link href={href} className="pillar-card__go">
        {cta} →
      </Link>
    </div>
  );
}
