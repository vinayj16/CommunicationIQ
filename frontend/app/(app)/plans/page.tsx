"use client";
import { useState, useEffect } from "react";
import { Check, CreditCard, Star, Zap, Building2, Crown } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { PageHeader, Skeleton, ErrorNote } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { API_BASE, getToken } from "@/lib/api";

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  seat_limit: number;
  features: string[];
  max_questions: number;
  max_exams_per_day: number;
  has_proctoring: boolean;
  has_analytics: boolean;
  has_custom_branding: boolean;
  has_api_access: boolean;
  is_active: boolean;
  is_default: boolean;
}

export default function PlansPage() {
  return (
    <RequireAuth roles={["student"]}>
      <Plans />
    </RequireAuth>
  );
}

function Plans() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const token = getToken();
        const res = await fetch(`${API_BASE}/student/plans`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          setPlans(data.filter((p: Plan) => p.is_active));
        }
      } catch (e) {
        setError("Failed to load plans");
      } finally {
        setLoading(false);
      }
    };
    loadPlans();
  }, []);

  const handleSubscribe = async (planId: string, planName: string) => {
    setSubscribing(planId);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/student/subscribe`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ plan_id: planId }),
      });
      if (res.ok) {
        toast("success", `Subscribed to ${planName} successfully!`);
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to subscribe");
      }
    } catch (e: any) {
      toast("error", e.message || "Failed to subscribe");
    } finally {
      setSubscribing(null);
    }
  };

  if (loading) return <Skeleton rows={4} />;
  if (error) return <ErrorNote message={error} />;

  const getPlanIcon = (slug: string) => {
    switch (slug) {
      case "free-trial": return <Star className="w-6 h-6" />;
      case "weekly-trial": return <Zap className="w-6 h-6" />;
      case "monthly-pro": return <Crown className="w-6 h-6" />;
      case "custom-enterprise": return <Building2 className="w-6 h-6" />;
      default: return <CreditCard className="w-6 h-6" />;
    }
  };

  const getPlanColor = (slug: string) => {
    switch (slug) {
      case "free-trial": return "var(--rag-green)";
      case "weekly-trial": return "var(--primary)";
      case "monthly-pro": return "var(--rag-amber)";
      case "custom-enterprise": return "var(--rag-violet)";
      default: return "var(--primary)";
    }
  };

  return (
    <>
      <PageHeader
        title="Subscription Plans"
        sub="Choose a plan that works for you. Upgrade anytime."
      />

      <div className="space-y-4">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className="ds-card p-5"
            style={{ borderColor: plan.is_default ? "var(--rag-green)" : undefined }}
          >
            <div className="flex flex-col md:flex-row md:items-start gap-4">
              {/* Left: Icon + Name + Price */}
              <div className="md:w-48 shrink-0">
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="p-2 rounded-full"
                    style={{ backgroundColor: `${getPlanColor(plan.slug)}20`, color: getPlanColor(plan.slug) }}
                  >
                    {getPlanIcon(plan.slug)}
                  </div>
                  <div>
                    <div className="font-bold text-sm">{plan.name}</div>
                    {plan.is_default && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "var(--rag-green)", color: "white" }}>
                        RECOMMENDED
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-2">
                  {plan.price_monthly === 0 ? (
                    <div className="text-2xl font-bold">Free</div>
                  ) : (
                    <div>
                      <span className="text-2xl font-bold">{'\u20B9'}{plan.price_monthly.toLocaleString()}</span>
                      <span className="text-xs text-muted">/month</span>
                      {plan.price_yearly > 0 && (
                        <div className="text-[10px] text-muted">
                          or {'\u20B9'}{plan.price_yearly.toLocaleString()}/year (save {Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100)}%)
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Middle: Description + Features */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted mb-3 leading-relaxed">{plan.description}</p>
                <ul className="space-y-1.5">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs">
                      <Check size={14} className="shrink-0 mt-0.5" style={{ color: "var(--rag-green)" }} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Right: Subscribe button */}
              <div className="md:w-36 shrink-0 flex md:justify-end">
                <button
                  onClick={() => handleSubscribe(plan.id, plan.name)}
                  disabled={subscribing === plan.id}
                  className="btn btn-primary btn-sm w-full md:w-auto"
                >
                  {subscribing === plan.id ? "Subscribing..." : plan.price_monthly === 0 ? "Get Started" : "Subscribe"}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {plans.length === 0 && !loading && (
        <div className="ds-card p-8 text-center text-muted">
          No plans available at the moment. Please check back later.
        </div>
      )}
    </>
  );
}
