import { useState } from "react";

const API_URL = "http://localhost:8000/api/audit";

function scoreColor(score) {
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-sky-400";
  if (score >= 50) return "text-amber-400";
  return "text-rose-400";
}

export default function App() {
  const [repository, setRepository] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState(null);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setReport(null);
    if (!repository.trim()) {
      setError("Repository URL/path is required.");
      return;
    }
    if (!pdfFile) {
      setError("PDF report is required.");
      return;
    }

    setLoading(true);
    try {
      const form = new FormData();
      form.append("repository", repository.trim());
      form.append("pdf_report", pdfFile);

      const response = await fetch(API_URL, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Audit request failed.");
      }
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <div className="mx-auto w-full max-w-6xl px-4 py-10">
        <h1 className="text-3xl font-semibold tracking-tight">The Automaton Bench</h1>
        <p className="mt-2 max-w-3xl text-slate-300">
          Digital Courtroom audit: detectives gather evidence, judges debate, chief justice issues final verdict.
        </p>

        <section className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/60 p-5 shadow-lg">
          <form className="grid gap-4" onSubmit={onSubmit}>
            <label className="grid gap-2">
              <span className="text-sm text-slate-300">Repository URL or local path</span>
              <input
                type="text"
                value={repository}
                onChange={(e) => setRepository(e.target.value)}
                placeholder="https://github.com/org/repo"
                className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 outline-none ring-sky-400 focus:ring-2"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm text-slate-300">PDF report</span>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-fit rounded-lg bg-sky-500 px-4 py-2 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {loading ? "Running audit..." : "Run courtroom audit"}
            </button>
          </form>
          {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
        </section>

        {report && (
          <section className="mt-8 grid gap-4">
            <article className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
              <h2 className="text-xl font-semibold">Final Verdict</h2>
              <p className={`mt-2 text-2xl font-bold ${scoreColor(report.final_verdict.score)}`}>
                {report.final_verdict.label} - {report.final_verdict.score}/100
              </p>
              <p className="mt-1 text-slate-300">Confidence: {report.final_verdict.confidence}</p>
            </article>

            <article className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
              <h3 className="text-lg font-semibold">Forensic Snapshot</h3>
              <div className="mt-3 grid gap-2 text-sm text-slate-200 md:grid-cols-2">
                <p>Python files: {report.evidence.python_files}</p>
                <p>Test files: {report.evidence.test_files}</p>
                <p>CI present: {String(report.evidence.ci_present)}</p>
                <p>Docs present: {String(report.evidence.docs_present)}</p>
                <p>Security docs: {String(report.evidence.security_docs_present)}</p>
                <p>PDF pages: {report.evidence.pdf_page_count}</p>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
              <h3 className="text-lg font-semibold">Judge Opinions</h3>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {report.judge_opinions.map((opinion) => (
                  <div key={opinion.judge_name} className="rounded-xl border border-slate-700 bg-slate-950/80 p-3">
                    <p className="font-medium">{opinion.judge_name}</p>
                    <p className="text-sm text-slate-300">Score: {opinion.score.total}/100</p>
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-300">
                      {opinion.rationale.slice(0, 3).map((item, idx) => (
                        <li key={`${opinion.judge_name}-${idx}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
              <h3 className="text-lg font-semibold">Unified Remediation Plan</h3>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-200">
                {report.final_verdict.remediation_plan.map((step, idx) => (
                  <li key={`fix-${idx}`}>{step}</li>
                ))}
              </ol>
            </article>
          </section>
        )}
      </div>
    </main>
  );
}
