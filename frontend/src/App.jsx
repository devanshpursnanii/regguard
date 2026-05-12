import React, { useEffect, useMemo, useState } from "react";
import { Routes, Route, Link, useNavigate, useParams } from "react-router-dom";
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const statusStyles = {
  MET: "bg-green/10 text-green border-green/30",
  PARTIAL: "bg-amber/10 text-amber border-amber/30",
  UNMET: "bg-red/10 text-red border-red/30"
};

const Skeleton = () => (
  <div className="animate-pulse space-y-3">
    <div className="h-4 w-1/3 rounded bg-slate-200" />
    <div className="h-4 w-full rounded bg-slate-200" />
    <div className="h-4 w-5/6 rounded bg-slate-200" />
  </div>
);

const UploadZone = ({ onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);

  const start = () => {
    if (running) return;
    setRunning(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        const next = Math.min(prev + 10, 100);
        if (next === 100) {
          clearInterval(interval);
          setRunning(false);
          onComplete();
        }
        return next;
      });
    }, 300);
  };

  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/90 p-6 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-lg font-semibold">Upload Compliance Documents</h3>
          <p className="text-sm text-slate-500">
            Drag and drop files here or click to simulate upload.
          </p>
        </div>
        <button
          onClick={start}
          className="rounded-full bg-navy px-4 py-2 text-sm font-semibold text-white"
        >
          Start Demo Upload
        </button>
      </div>
      {running && (
        <div className="mt-4">
          <div className="h-2 w-full rounded-full bg-slate-200">
            <div
              className="h-2 rounded-full bg-green transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">Processing {progress}%</p>
        </div>
      )}
    </div>
  );
};

const ScoreRing = ({ score }) => {
  const color = score >= 80 ? "#22c55e" : score >= 70 ? "#f59e0b" : "#ef4444";
  const data = [{ name: "score", value: score, fill: color }];
  return (
    <div className="h-28 w-28">
      <ResponsiveContainer>
        <RadialBarChart
          innerRadius="70%"
          outerRadius="100%"
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" cornerRadius={10} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="-mt-20 text-center text-lg font-semibold text-slate-900">
        {score}%
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API_BASE}/api/companies`)
      .then((res) => res.json())
      .then((data) => setCompanies(data))
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div className="rounded-3xl bg-navy px-6 py-8 text-white shadow-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-slate-300">RBI Compliance Desk</p>
            <h1 className="mt-3 text-3xl font-semibold">RegGuard Risk Intelligence</h1>
            <p className="mt-2 text-sm text-slate-200">
              Automated gap analysis, evidence mapping, and audit-ready reports.
            </p>
          </div>
          <div className="rounded-2xl bg-white/10 px-6 py-4">
            <p className="text-xs uppercase text-slate-300">Today</p>
            <p className="text-2xl font-semibold">3 companies</p>
            <p className="text-xs text-slate-300">Analysed overnight</p>
          </div>
        </div>
      </div>

      <UploadZone onComplete={() => {}} />

      <div>
        <h2 className="text-xl font-semibold">Companies analysed overnight</h2>
        <p className="text-sm text-slate-500">
          Ingestion pipeline ran overnight. Select a company to review gaps.
        </p>
      </div>

      {loading ? (
        <Skeleton />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {companies.map((company) => (
            <button
              key={company.id}
              onClick={() => navigate(`/company/${company.id}`)}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/90 p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">{company.status}</p>
                <h3 className="text-lg font-semibold">{company.name}</h3>
                <p className="text-xs text-slate-500">Compliance score</p>
              </div>
              <ScoreRing score={company.overall_score} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const GapMatrixTable = ({ clauses }) => {
  const [sortKey, setSortKey] = useState("status");
  const sorted = useMemo(() => {
    return [...clauses].sort((a, b) => {
      if (sortKey === "confidence") {
        return b.confidence - a.confidence;
      }
      return a.status.localeCompare(b.status);
    });
  }, [clauses, sortKey]);

  return (
    <div className="overflow-auto rounded-xl border border-slate-200 bg-white/95">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 className="font-semibold">Gap Matrix</h3>
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value)}
          className="rounded-full border border-slate-200 px-3 py-1 text-sm"
        >
          <option value="status">Sort by status</option>
          <option value="confidence">Sort by confidence</option>
        </select>
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-4 py-2 text-left">Clause</th>
            <th className="px-4 py-2 text-left">Section</th>
            <th className="px-4 py-2 text-left">Status</th>
            <th className="px-4 py-2 text-left">Confidence</th>
            <th className="px-4 py-2 text-left">Citation</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((clause) => (
            <tr key={clause.clause_id} className="border-t border-slate-100">
              <td className="px-4 py-3">{clause.clause_number}</td>
              <td className="px-4 py-3">{clause.section}</td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                    statusStyles[clause.status]
                  }`}
                >
                  {clause.status}
                </span>
              </td>
              <td className="px-4 py-3">{Math.round(clause.confidence * 100)}%</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-500">
                {clause.regulatory_citation} {clause.company_citation}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const EvidencePanel = ({ pairs }) => (
  <div className="space-y-4">
    {pairs.map((pair, index) => (
      <div
        key={index}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white/95 p-4 md:grid-cols-2"
      >
        <div>
          <p className="text-xs font-semibold text-slate-500">Regulatory</p>
          <p className="mt-2 text-sm">{pair.regulatory_sentence}</p>
          <p className="mt-3 text-xs font-mono text-slate-500">{pair.regulatory_citation}</p>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-500">Company</p>
          <p className="mt-2 text-sm">{pair.company_sentence}</p>
          <p className="mt-3 text-xs font-mono text-slate-500">{pair.company_citation}</p>
        </div>
      </div>
    ))}
  </div>
);

const ChatDrawer = ({ open, onClose, companyId }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [email, setEmail] = useState("demo@regguard.ai");

  const send = async () => {
    if (!input.trim()) return;
    const next = [...messages, { role: "user", text: input }];
    setMessages(next);
    setInput("");
    setLoading(true);
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: companyId, message: input })
    });
    const data = await res.json();
    setMessages([...next, { role: "assistant", text: data.answer, citations: data.citations || [] }]);
    setLoading(false);
  };

  const generateReport = async () => {
    setToast("");
    await fetch(`${API_BASE}/api/report/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: companyId, email })
    });
    setToast(`Report sent to ${email}`);
    setTimeout(() => setToast(""), 3000);
  };

  const highlightCitations = (text) => {
    return text.split(/(\[[^\]]+\])/g).map((part, idx) => {
      if (part.startsWith("[")) {
        return (
          <span
            key={idx}
            className="mx-1 inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
          >
            {part}
          </span>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div
      className={`fixed right-0 top-0 h-full w-full max-w-md transform bg-white shadow-2xl transition-transform ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="flex h-full flex-col">
        <div className="border-b border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Ask RegGuard</h3>
            <button onClick={onClose} className="text-sm text-slate-500">
              Close
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-full border border-slate-200 px-3 py-1 text-sm"
              placeholder="your@email.com"
            />
            <button
              onClick={generateReport}
              className="rounded-full bg-navy px-3 py-1 text-sm text-white"
            >
              Generate Report
            </button>
          </div>
          {toast && <p className="mt-2 text-xs text-green">{toast}</p>}
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.role === "user" ? "text-right" : "text-left"}>
              <div
                className={`inline-block rounded-2xl px-4 py-2 text-sm ${
                  msg.role === "user" ? "bg-navy text-white" : "bg-slate-100"
                }`}
              >
                {highlightCitations(msg.text)}
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <details className="mt-2 text-xs text-slate-500">
                  <summary>Sources</summary>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {msg.citations.map((citation) => (
                      <span key={citation} className="rounded-full bg-slate-200 px-2 py-0.5">
                        {citation}
                      </span>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
          {loading && <p className="text-sm text-slate-500">Thinking...</p>}
        </div>
        <div className="border-t border-slate-200 p-4">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 rounded-full border border-slate-200 px-4 py-2 text-sm"
              placeholder="Ask about compliance..."
            />
            <button onClick={send} className="rounded-full bg-navy px-4 py-2 text-sm text-white">
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const CompanyDetail = () => {
  const { id } = useParams();
  const [gapMatrix, setGapMatrix] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [tab, setTab] = useState("gap");
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setGapMatrix(null);
    setEvidence(null);
    fetch(`${API_BASE}/api/gap-matrix/${id}`)
      .then((res) => res.json())
      .then((data) => setGapMatrix(data));
    fetch(`${API_BASE}/api/evidence/${id}`)
      .then((res) => res.json())
      .then((data) => setEvidence(data));
  }, [id]);

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <aside className="w-full rounded-2xl bg-navy p-5 text-white lg:w-64">
        <h3 className="text-lg font-semibold">Regulations</h3>
        <div className="mt-4 space-y-3">
          {gapMatrix ? (
            gapMatrix.regulations.map((reg) => (
              <div key={reg.id} className="rounded-xl bg-white/10 p-3">
                <p className="text-sm font-semibold">{reg.title}</p>
                <p className="text-xs text-slate-200">Score {reg.score}%</p>
              </div>
            ))
          ) : (
            <Skeleton />
          )}
        </div>
      </aside>
      <main className="flex-1 space-y-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold">{gapMatrix?.company_name || "Company"}</h2>
            <p className="text-sm text-slate-500">Compliance overview with citations</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setTab("gap")}
              className={`rounded-full px-4 py-2 text-sm ${
                tab === "gap" ? "bg-navy text-white" : "border border-slate-200"
              }`}
            >
              Gap Matrix
            </button>
            <button
              onClick={() => setTab("evidence")}
              className={`rounded-full px-4 py-2 text-sm ${
                tab === "evidence" ? "bg-navy text-white" : "border border-slate-200"
              }`}
            >
              Evidence
            </button>
          </div>
        </div>
        {!gapMatrix ? (
          <Skeleton />
        ) : tab === "gap" ? (
          <GapMatrixTable clauses={gapMatrix.clauses} />
        ) : (
          evidence && <EvidencePanel pairs={evidence.pairs} />
        )}
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 rounded-full bg-navy px-4 py-3 text-sm font-semibold text-white shadow-lg"
        >
          Ask RegGuard
        </button>
        <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} companyId={id} />
      </main>
    </div>
  );
};

const Layout = ({ children }) => (
  <div className="min-h-screen">
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="text-xl font-bold text-navy">
          RegGuard
        </Link>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="rounded-full bg-green/10 px-3 py-1 text-green">Pipeline healthy</span>
          <span>AI Compliance Intelligence</span>
        </div>
      </div>
    </header>
    <div className="mx-auto max-w-6xl px-6 py-6">{children}</div>
  </div>
);

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/company/:id" element={<CompanyDetail />} />
      </Routes>
    </Layout>
  );
}
