"use client";
import { useState } from "react";
import { Send, CheckCircle, AlertTriangle } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function ContactPage() {
  return (
    <RequireAuth roles={["student", "tenant_admin"]}>
      <Contact />
    </RequireAuth>
  );
}

function Contact() {
  const { toast } = useToast();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("normal");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!subject.trim() || !body.trim()) {
      setError("Subject and message are required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await api.submitContactMessage({ subject: subject.trim(), body: body.trim(), priority });
      setSent(true);
      toast("success", "Message sent");
    } catch (e: any) {
      setError(e?.detail || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <>
        <PageHeader title="Contact Us" sub="Send a message to our support team" />
        <div className="ds-card p-8 text-center">
          <CheckCircle size={48} className="mx-auto mb-4" style={{ color: "var(--rag-green)" }} />
          <div className="text-lg font-bold mb-2">Message Sent!</div>
          <div className="text-sm text-muted mb-4">
            Thank you for reaching out. Our team will get back to you soon.
          </div>
          <button onClick={() => { setSent(false); setSubject(""); setBody(""); }}
            className="px-4 py-2 text-xs rounded-md text-white" style={{ background: "var(--brand-grad)" }}>
            Send Another Message
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Contact Us" sub="Have a question or need help? Send us a message." />

      <div className="ds-card p-5 max-w-xl">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-md mb-4 text-xs"
            style={{ background: "color-mix(in srgb, var(--rag-red) 10%, transparent)", color: "var(--rag-red)" }}>
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1">Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)}
              placeholder="What is this about?"
              className="w-full px-3 py-2 text-xs rounded-md border bg-transparent"
              style={{ borderColor: "var(--border)" }} />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}
              className="px-3 py-2 text-xs rounded-md border bg-transparent"
              style={{ borderColor: "var(--border)" }}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">Message</label>
            <textarea value={body} onChange={(e) => setBody(e.target.value)}
              rows={6} placeholder="Describe your question or issue..."
              className="w-full px-3 py-2 text-xs rounded-md border bg-transparent resize-y"
              style={{ borderColor: "var(--border)" }} />
          </div>

          <div className="flex justify-end">
            <button onClick={handleSubmit} disabled={loading || !subject.trim() || !body.trim()}
              className="px-4 py-2 text-xs rounded-md text-white flex items-center gap-2 disabled:opacity-50"
              style={{ background: "var(--brand-grad)" }}>
              {loading ? "Sending..." : <><Send size={12} /> Send Message</>}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
