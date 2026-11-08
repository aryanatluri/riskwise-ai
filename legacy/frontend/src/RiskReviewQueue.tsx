import React, { useState, useEffect } from "react";
import { ShieldAlert, AlertTriangle, CheckCircle2, XCircle, ArrowRight, Loader2, FileText, Send, Building2 } from "lucide-react";

interface ReviewSummary {
  thread_id: string;
  contract_id: string;
  contract_title: string;
  counterparty: string;
  section_title: string;
  page_number: number;
  highest_severity: string;
  composite_risk_score: number;
  pending_actions_count: number;
}

export default function RiskReviewQueue() {
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [selectedThread, setSelectedThread] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [redlineText, setRedlineText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dispatchedSuccess, setDispatchedSuccess] = useState<any>(null);

  useEffect(() => {
    fetch("/api/v1/reviews/pending")
      .then(res => res.json())
      .then(data => {
        setReviews(data);
        if (data.length > 0) {
          setSelectedThread(data[0].thread_id);
        }
      });
  }, []);

  useEffect(() => {
    if (selectedThread) {
      fetch(`/api/v1/reviews/${selectedThread}`)
        .then(res => res.json())
        .then(data => {
          setDetail(data);
          if (data.pending_actions && data.pending_actions.length > 0) {
            setRedlineText(data.pending_actions[0].proposed_redline);
          }
        });
    }
  }, [selectedThread]);

  const handleApprove = async () => {
    if (!detail || !selectedThread) return;
    setIsSubmitting(true);
    const actionId = detail.pending_actions?.[0]?.action_id || "act-default";
    const res = await fetch(`/api/v1/reviews/${selectedThread}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reviewer_email: "compliance-officer@apexfinancial.com",
        decisions: [{
          action_id: actionId,
          approved: true,
          override_redline: redlineText
        }]
      })
    });
    const result = await res.json();
    setIsSubmitting(false);
    setDispatchedSuccess(result);
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar: Pending Reviews List */}
      <aside className="w-80 border-r border-slate-800 p-4 flex flex-col">
        <div className="flex items-center space-x-2 mb-4">
          <ShieldAlert className="w-5 h-5 text-indigo-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Pending Human Approvals ({reviews.length})
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto space-y-2">
          {reviews.map(r => (
            <div
              key={r.thread_id}
              onClick={() => { setSelectedThread(r.thread_id); setDispatchedSuccess(null); }}
              className={`p-3 rounded-lg cursor-pointer transition border ${
                selectedThread === r.thread_id
                  ? "bg-indigo-900/40 border-indigo-500 shadow-md shadow-indigo-950"
                  : "bg-slate-900 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  r.highest_severity === "CRITICAL" ? "bg-red-950 text-red-400 border border-red-800" : "bg-amber-950 text-amber-400 border border-amber-800"
                }`}>
                  {r.highest_severity}
                </span>
                <span className="text-[11px] font-mono text-indigo-300 font-semibold">
                  CRS: {r.composite_risk_score}
                </span>
              </div>
              <h4 className="text-sm font-semibold text-slate-200 mt-2 line-clamp-1">{r.section_title}</h4>
              <p className="text-xs text-slate-400 mt-0.5 truncate">{r.counterparty || r.contract_title}</p>
              <p className="text-[11px] text-slate-500 mt-1">Page {r.page_number} • 1 action pending</p>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Review Area */}
      <main className="flex-1 p-8 overflow-y-auto">
        {detail ? (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-xs font-mono text-indigo-400 uppercase tracking-wider">
                  Checkpointed Thread: {detail.thread_id}
                </span>
                <h1 className="text-2xl font-bold text-white mt-1">{detail.section_title}</h1>
                <p className="text-xs text-slate-400">{detail.contract_title} • Page {detail.page_number}</p>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400 block">Composite Risk Score</span>
                <span className="text-2xl font-extrabold text-red-400">
                  {detail.quantitative_metrics?.composite_risk_score} / 10.0
                </span>
              </div>
            </div>

            {/* Evidence Block */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-slate-400" />
                Stage 1: Contractual Evidence (Verbatim Quote)
              </h3>
              <blockquote className="border-l-4 border-indigo-500 pl-4 py-2 italic text-slate-200 bg-slate-950/50 rounded-r font-serif text-sm">
                "{detail.raw_clause_text}"
              </blockquote>
            </div>

            {/* Benchmarks Comparison */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs uppercase font-bold text-blue-400 mb-2">Corporate Policy Benchmark</h4>
                {detail.retrieved_policies?.map((p: any, i: number) => (
                  <div key={i} className="text-xs space-y-1">
                    <p className="font-semibold text-slate-300">{p.policy_code}: {p.title || p.clause_code}</p>
                    <p className="text-slate-400">{p.mandate}</p>
                    {p.delta && <p className="text-amber-400 font-mono text-[11px] pt-1">{p.delta}</p>}
                  </div>
                ))}
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs uppercase font-bold text-red-400 mb-2">Statutory Mandates Benchmark</h4>
                {detail.retrieved_regulations?.map((r: any, i: number) => (
                  <div key={i} className="text-xs space-y-1 mb-2 border-b border-slate-800/60 pb-2 last:border-0">
                    <p className="font-semibold text-slate-300">{r.regulation_name || r.regulation} ({r.section || ""})</p>
                    <p className="text-slate-400">{r.rule || r.mandate_sla || ""}</p>
                    {r.exposure && <p className="text-rose-400 font-mono text-[11px]">{r.exposure}</p>}
                  </div>
                ))}
              </div>
            </div>

            {/* Redline Editor */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                <span>Stage 4: Mandatory Replacement Legal Redline</span>
                <span className="text-[11px] text-emerald-400 font-mono">Editable by Compliance Officer</span>
              </h3>
              <textarea
                rows={4}
                value={redlineText}
                onChange={e => setRedlineText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-emerald-400 font-mono text-xs focus:outline-none focus:border-indigo-500 mb-4 transition"
              />
              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-slate-400">
                  Assigned Infosec Owner: <span className="text-slate-200 font-semibold">{detail.pending_actions?.[0]?.suggested_owner}</span>
                </div>
                <button
                  onClick={handleApprove}
                  disabled={isSubmitting}
                  className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm px-6 py-2.5 rounded-lg transition shadow-lg shadow-indigo-600/30"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Authorize & Resume LangGraph Engine</span>}
                </button>
              </div>
            </div>

            {/* Success Banner */}
            {dispatchedSuccess && (
              <div className="bg-emerald-950/80 border border-emerald-600 rounded-xl p-4 text-xs text-emerald-200">
                <p className="font-bold text-sm text-emerald-400 flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> Workflow Resumed & Enterprise Actions Dispatched!
                </p>
                <p>Jira Issue created with Highest priority. Interactive Slack alert card sent to #compliance-risk-alerts.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500">
            Select a risk checkpoint from the queue to review
          </div>
        )}
      </main>
    </div>
  );
}
