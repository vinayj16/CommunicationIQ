"use client";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowRight, TriangleAlert } from "lucide-react";
import { Badge, PageHeader, Section } from "@/components/ui";

/** The page for a skill that is not finished yet.
 *
 *  Every one of these could have been left out of the menu until it worked.
 *  That is the tidier option and the worse one: a student cannot tell the
 *  difference between a feature that does not exist and a feature they have
 *  not found, so the app reads as broken rather than as honest about its own
 *  edges — and they go looking for a Listening section that was never there.
 *
 *  So each unfinished skill gets a real page that does three things: says
 *  plainly what does not work, sends the student to the nearest thing that
 *  does, and describes what would have to be built. No progress bars over
 *  nothing, no "coming soon" with no date behind it.
 */
export function ModuleShell({
  icon: Icon, title, standfirst, whatWorks, whatIsMissing, needed, tone,
}: {
  icon: LucideIcon;
  title: string;
  standfirst: string;
  /** The nearest real thing, or null when there genuinely isn't one. */
  whatWorks: { href: string; label: string; detail: string } | null;
  whatIsMissing: string[];
  needed: string;
  tone: string;
}) {
  return (
    <>
      <PageHeader
        title={title}
        sub={standfirst}
        action={
          <Badge tone={tone}>
            <TriangleAlert size={9} /> {whatWorks ? "Partly built" : "Not built"}
          </Badge>
        }
      />

      {whatWorks ? (
        <Section title="What you can practise today" className="mb-4">
          <Link href={whatWorks.href}
                className="ds-card p-4 hover:bg-surface2 transition-colors ds-focus flex items-center gap-3">
            <span className="rounded-full p-2 shrink-0"
                  style={{ background: `color-mix(in srgb, ${tone} 14%, transparent)` }}>
              <Icon size={17} style={{ color: tone }} />
            </span>
            <div className="flex-1">
              <div className="text-sm font-bold">{whatWorks.label}</div>
              <p className="text-xs text-muted mt-0.5 leading-relaxed">
                {whatWorks.detail}
              </p>
            </div>
            <ArrowRight size={16} className="text-muted shrink-0" />
          </Link>
        </Section>
      ) : (
        <div className="ds-card p-4 mb-4" style={{ borderColor: tone }}>
          <div className="text-sm font-bold mb-1">There is nothing here yet</div>
          <p className="text-xs text-muted leading-relaxed">
            Not a screen, not an item, not a scorer. This page exists so the
            gap is visible on the menu instead of being something you find out
            by looking for it.
          </p>
        </div>
      )}

      <Section title="What is missing" className="mb-4">
        <ul className="space-y-2">
          {whatIsMissing.map((line) => (
            <li key={line} className="flex items-start gap-2 text-xs text-muted leading-relaxed">
              <span className="mt-1.5 shrink-0 rounded-full"
                    style={{ width: 4, height: 4, background: "var(--muted)" }} />
              {line}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="What it would take">
        <p className="text-xs text-muted leading-relaxed">{needed}</p>
        <Link href="/skills"
              className="btn btn-ghost btn-sm ds-focus mt-3 inline-flex">
          See all four skills
        </Link>
      </Section>
    </>
  );
}
