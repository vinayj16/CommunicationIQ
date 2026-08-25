"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRole } from "@/components/RoleProvider";
import { landingFor } from "@/lib/nav";

/** Front door. Sends each role to the screen that is actually their job. */
export default function Index() {
  const { user, loading } = useRole();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? landingFor(user.role) : "/login");
  }, [user, loading, router]);

  return <div className="p-8 text-xs text-muted">Opening Fluenzee AI…</div>;
}
