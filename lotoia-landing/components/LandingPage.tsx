"use client";

import { useState } from "react";

import { Footer } from "@/components/Footer";
import { Form } from "@/components/Form";
import { Hero } from "@/components/Hero";
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
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-lg font-black text-white">
            L
          </div>
          <span className="text-lg font-bold tracking-wide text-white">LotoIA</span>
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
