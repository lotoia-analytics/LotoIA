"use client";

import { useState } from "react";

import { Footer } from "@/components/Footer";
import { Form } from "@/components/Form";
import { Hero } from "@/components/Hero";
import { Logo } from "@/components/Logo";
import { HowItWorks } from "@/components/HowItWorks";
import { Plans } from "@/components/Plans";
import type { PlanId } from "@/lib/plans";

export function LandingPage() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  function openPlans() {
    document.getElementById("planos")?.scrollIntoView({ behavior: "smooth" });
  }

  function openForm(planId: PlanId) {
    setSelectedPlan(planId);
    setIsFormOpen(true);
  }

  return (
    <main>
      <header className="px-4 pt-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <Logo />
        </div>
      </header>

      <Hero onCtaClick={openPlans} />
      <HowItWorks />
      <Plans onSelectPlan={openForm} />
      <Footer />

      <Form
        isOpen={isFormOpen}
        selectedPlan={selectedPlan}
        onClose={() => setIsFormOpen(false)}
      />
    </main>
  );
}
