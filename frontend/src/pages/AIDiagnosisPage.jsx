import React, { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api/axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
  LineChart, Line, CartesianGrid,
} from 'recharts'
import {
  Brain, Search, X, AlertTriangle, ShieldAlert, CheckCircle2, RefreshCw, Sparkles, HelpCircle, Plus,
  Activity, GraduationCap, History, Network, Stethoscope, ClipboardList, FlaskConical, Building2,
  ChevronDown, ChevronUp, ListChecks,
} from 'lucide-react'

const EMPTY_FORM = {
  patient_name: '', age: '', gender: '', temperature: '', heart_rate: '', systolic_bp: '', spo2: '',
  duration_days: '', history_text: '',
}
const pretty = (s) => s.replace(/_/g, ' ')
const cap = (s) => pretty(s).charAt(0).toUpperCase() + pretty(s).slice(1)
const inputCls = 'w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500'
const PRIORITY_CLS = {
  Urgent: 'bg-rose-600 text-white', High: 'bg-amber-500 text-white', Routine: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
}
const LEVEL_CLS = {
  Likely: 'bg-blue-600 text-white', Possible: 'bg-blue-100 text-blue-800', 'Less likely': 'bg-slate-100 text-slate-600',
  Unlikely: 'bg-slate-50 text-slate-400', 'Must rule out': 'bg-rose-100 text-rose-700', 'Best evidence fit': 'bg-emerald-600 text-white',
}

function Card({ title, icon: Icon, right, children, className = '' }) {
  return (
    <section className={`bg-white rounded-2xl border border-slate-200 shadow-sm ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-2 px-5 py-3.5 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-blue-600" />} {title}
          </h3>
          {right}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

function Field({ label, unit, children }) {
  return (
    <label className="block">
      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
        {label} {unit && <span className="normal-case font-normal text-slate-400">({unit})</span>}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  )
}

export default function AIDiagnosisPage() {
  const [schema, setSchema] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [symptoms, setSymptoms] = useState([])
  const [search, setSearch] = useState('')
  const [group, setGroup] = useState('All')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [showAll, setShowAll] = useState(false)
  const [confirmed, setConfirmed] = useState('')
  const [notes, setNotes] = useState('')
  const [feedbackMsg, setFeedbackMsg] = useState(null)
  const [info, setInfo] = useState(null)
  const [patternDisease, setPatternDisease] = useState('Dengue')
  const [pattern, setPattern] = useState(null)
  const [cases, setCases] = useState([])
  const [retraining, setRetraining] = useState(false)

  const loadInfo = useCallback(async () => {
    try {
      const [i, c] = await Promise.all([api.get('/api/ai/model-info'), api.get('/api/ai/cases?limit=8')])
      setInfo(i.data); setCases(c.data)
    } catch (e) { console.error(e) }
  }, [])

  useEffect(() => {
    api.get('/api/ai/schema').then((r) => setSchema(r.data)).catch(() => setError('Cannot reach the AI service on the backend.'))
    loadInfo()
  }, [loadInfo])

  useEffect(() => {
    if (!patternDisease) return
    setPattern(null)
    api.get(`/api/ai/patterns?disease=${encodeURIComponent(patternDisease)}&top_k=8`).then((r) => setPattern(r.data)).catch(() => {})
  }, [patternDisease, info?.version])

  useEffect(() => {
    if (!info?.retrain_status?.running) return
    const t = setInterval(loadInfo, 2000)
    return () => clearInterval(t)
  }, [info?.retrain_status?.running, loadInfo])

  const groups = useMemo(() => (schema ? ['All', ...Object.keys(schema.symptom_groups)] : ['All']), [schema])
  const visibleSymptoms = useMemo(() => {
    if (!schema) return []
    const base = group === 'All' ? schema.all_symptoms : schema.symptom_groups[group] || []
    const q = search.trim().toLowerCase().replace(/ /g, '_')
    return base.filter((s) => !q || s.includes(q))
  }, [schema, group, search])
  const toggle = (s) => setSymptoms((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]))

  const runDiagnosis = async (symList = symptoms) => {
    if (symList.length === 0) { setError('Select at least one symptom.'); return }
    setLoading(true); setError(''); setFeedbackMsg(null)
    try {
      const clinical = {}
      for (const k of ['age', 'temperature', 'heart_rate', 'systolic_bp', 'spo2', 'duration_days']) if (form[k] !== '') clinical[k] = Number(form[k])
      if (form.gender) clinical.gender = form.gender
      const r = await api.post('/api/ai/diagnose', {
        symptoms: symList, clinical, patient_name: form.patient_name || null, history_text: form.history_text,
      })
      setResult(r.data); setConfirmed(r.data.top3_predictions[0].disease); setNotes(''); setShowAll(false)
      loadInfo()
    } catch (e) {
      setError(e.response?.data?.error || e.response?.data?.detail || 'Diagnosis failed.')
    } finally { setLoading(false) }
  }
  const addFollowUp = (s) => { const n = symptoms.includes(s) ? symptoms : [...symptoms, s]; setSymptoms(n); runDiagnosis(n) }
  const sendFeedback = async () => {
    if (!result?.prediction_id || !confirmed) return
    try {
      const r = await api.post('/api/ai/feedback', { prediction_id: result.prediction_id, confirmed_diagnosis: confirmed, notes })
      setFeedbackMsg({ ok: true, text: r.data.message }); loadInfo()
    } catch (e) { setFeedbackMsg({ ok: false, text: e.response?.data?.message || e.response?.data?.detail || 'Could not save feedback.' }) }
  }
  const retrainNow = async () => {
    setRetraining(true)
    try { const r = await api.post('/api/ai/retrain', {}); setFeedbackMsg({ ok: r.data.accepted !== false, text: r.data.message }) }
    catch { setFeedbackMsg({ ok: false, text: 'Retraining failed.' }) }
    finally { setRetraining(false); loadInfo() }
  }
  const reset = () => { setForm(EMPTY_FORM); setSymptoms([]); setResult(null); setError(''); setFeedbackMsg(null) }

  const shapData = (result?.shap_attribution?.items || []).slice(0, 10).map((a) => ({
    name: `${a.label}${a.present ? '' : ' (absent)'}`, value: a.value, present: a.present,
  }))
  const rs = info?.research_metrics
  const versionData = (info?.history || []).filter((h) => h.accepted && h.benchmark).map((h, i) => ({
    name: `v${h.version}${h.kind === 'rollback' ? 'r' : ''}`, accuracy: +(h.benchmark.accuracy * 100).toFixed(2),
  }))
  const curve = info?.last_training_curve
  const curveData = curve ? curve.epoch.map((e, i) => ({ epoch: e, loss: curve.train_loss[i] })) : []
  const cr = result?.clinical_reasoning
  const tri = result?.triage

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mb-2">
            <Brain className="w-3.5 h-3.5" /> D1-trained MLP · Kernel SHAP · independent triage
          </span>
          <h1 className="text-2xl font-bold text-slate-800">AI Diagnosis Assistant</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Scores all 41 diseases, explains the result with Kernel SHAP, triages independently of the model,
            and writes a clinical reasoning report with tests and next steps.
          </p>
        </div>
        {info && (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600">Model <b className="text-slate-800">v{info.version}</b></span>
            {rs?.cv_macro_f1 != null && <span className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600">CV macro-F1 <b className="text-slate-800">{rs.cv_macro_f1.toFixed(3)}</b></span>}
            {rs?.robustness && <span className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600">50% symptoms missing <b className="text-slate-800">{(rs.robustness.drop_50pct.accuracy * 100).toFixed(1)}%</b></span>}
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* ------------------------------------------------ FORM */}
        <div className="lg:col-span-2 space-y-6">
          <Card title="Patient, vitals & history" icon={Stethoscope}
            right={<button onClick={reset} className="text-xs text-slate-400 hover:text-slate-700">Clear</button>}>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2"><Field label="Patient name" unit="optional">
                <input className={inputCls} value={form.patient_name} onChange={(e) => setForm({ ...form, patient_name: e.target.value })} placeholder="e.g. Ravi Kumar" />
              </Field></div>
              <Field label="Age" unit="years"><input type="number" className={inputCls} value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} placeholder="35" /></Field>
              <Field label="Sex"><select className={inputCls} value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                <option value="">Not specified</option><option value="F">Female</option><option value="M">Male</option></select></Field>
              <Field label="Temperature" unit="°C"><input type="number" step="0.1" className={inputCls} value={form.temperature} onChange={(e) => setForm({ ...form, temperature: e.target.value })} placeholder="37.0" /></Field>
              <Field label="Heart rate" unit="bpm"><input type="number" className={inputCls} value={form.heart_rate} onChange={(e) => setForm({ ...form, heart_rate: e.target.value })} placeholder="80" /></Field>
              <Field label="Systolic BP" unit="mmHg"><input type="number" className={inputCls} value={form.systolic_bp} onChange={(e) => setForm({ ...form, systolic_bp: e.target.value })} placeholder="120" /></Field>
              <Field label="SpO₂" unit="%"><input type="number" className={inputCls} value={form.spo2} onChange={(e) => setForm({ ...form, spo2: e.target.value })} placeholder="98" /></Field>
              <div className="col-span-2"><Field label="Symptoms started" unit="days ago">
                <input type="number" className={inputCls} value={form.duration_days} onChange={(e) => setForm({ ...form, duration_days: e.target.value })} placeholder="3" />
              </Field></div>
              <div className="col-span-2"><Field label="History / complaint" unit="free text, used by triage">
                <textarea rows={2} className={inputCls} value={form.history_text} onChange={(e) => setForm({ ...form, history_text: e.target.value })} placeholder="e.g. fever for 3 days, recent travel, known diabetic" />
              </Field></div>
            </div>
            <p className="text-[11px] text-slate-400 mt-3">The disease model uses symptoms; vitals and history drive triage, red flags and the reasoning report.</p>
          </Card>

          <Card title={`Symptoms (${symptoms.length} selected)`} icon={Activity}>
            {symptoms.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {symptoms.map((s) => (
                  <button key={s} onClick={() => toggle(s)} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-600 text-white hover:bg-blue-700">
                    {pretty(s)} <X className="w-3 h-3" />
                  </button>
                ))}
              </div>
            )}
            <div className="relative mb-3">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input className={`${inputCls} pl-9`} placeholder="Search 131 symptoms…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <div className="flex gap-1 overflow-x-auto pb-2 mb-2">
              {groups.map((g) => (
                <button key={g} onClick={() => setGroup(g)} className={`whitespace-nowrap px-2.5 py-1 rounded-md text-[11px] font-semibold ${group === g ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{g}</button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-56 overflow-y-auto">
              {visibleSymptoms.map((s) => (
                <button key={s} onClick={() => toggle(s)} className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${symptoms.includes(s) ? 'bg-blue-50 border-blue-400 text-blue-700 font-semibold' : 'bg-white border-slate-200 text-slate-600 hover:border-blue-300'}`}>{pretty(s)}</button>
              ))}
            </div>
          </Card>

          {error && <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm"><AlertTriangle className="w-4 h-4" /> {error}</div>}
          <button onClick={() => runDiagnosis()} disabled={loading || symptoms.length === 0}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 text-white font-semibold text-sm shadow-md shadow-blue-500/20 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? 'Analysing…' : 'Run AI diagnosis'}
          </button>
        </div>

        {/* ------------------------------------------------ RESULTS */}
        <div className="lg:col-span-3 space-y-6">
          {!result && (
            <div className="h-full min-h-[420px] flex flex-col items-center justify-center text-center bg-white rounded-2xl border border-dashed border-slate-300 p-10">
              <Network className="w-12 h-12 text-slate-300 mb-3" />
              <p className="font-semibold text-slate-600">No diagnosis yet</p>
              <p className="text-sm text-slate-400 max-w-sm mt-1">Pick the patient's symptoms (add vitals and history if available), then run the AI diagnosis.</p>
            </div>
          )}

          {result && (
            <>
              {tri?.red_flag_reasons?.length > 0 && (
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
                  <p className="font-bold text-rose-700 flex items-center gap-2 text-sm"><ShieldAlert className="w-4 h-4" /> Red flags (rule-based, independent of the AI model)</p>
                  <ul className="mt-2 space-y-1 text-sm text-rose-700 list-disc pl-6">{tri.red_flag_reasons.map((f, i) => <li key={i}>{f}</li>)}</ul>
                </div>
              )}

              <Card title="Triage & department recommendation" icon={Building2}
                right={<span className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${PRIORITY_CLS[tri.priority]}`}>Priority: {tri.priority}</span>}>
                <div className="grid sm:grid-cols-2 gap-2">
                  {tri.recommended_departments.map((d, i) => (
                    <div key={d.department} className={`p-3 rounded-xl border ${i === 0 ? 'border-blue-200 bg-blue-50/40' : 'border-slate-200'}`}>
                      <p className="text-sm font-bold text-slate-800">{i + 1}. {d.department} <span className="text-xs font-normal text-slate-400">score {d.score}</span></p>
                      <p className="text-xs text-slate-500 mt-0.5">{d.justification}</p>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-2">Severity score {tri.severity_score} (D2 symptom-severity weights). {tri.method}.</p>
              </Card>

              <Card title="Differential diagnosis" icon={Brain}
                right={<span className="text-[11px] text-slate-400">{result.model.type} · v{result.model.version}</span>}>
                <div className="space-y-3">
                  {result.top3_predictions.map((p, i) => (
                    <div key={p.disease} className={`p-4 rounded-xl border ${i === 0 ? 'border-blue-200 bg-blue-50/40' : 'border-slate-200'}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={`font-bold ${i === 0 ? 'text-slate-900 text-base' : 'text-slate-700 text-sm'}`}>{i + 1}. {p.disease}</p>
                          <p className="text-xs text-slate-500">{p.department} · urgency {p.urgency}</p>
                        </div>
                        <span className={`font-bold tabular-nums ${i === 0 ? 'text-blue-700 text-xl' : 'text-slate-600'}`}>{p.percentage}%</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full mt-2 overflow-hidden"><div className={`h-full rounded-full ${i === 0 ? 'bg-blue-600' : 'bg-slate-400'}`} style={{ width: `${Math.max(1, p.percentage)}%` }} /></div>
                      {i === 0 && <p className="text-sm text-slate-600 mt-3">{p.description}</p>}
                    </div>
                  ))}
                </div>
                <button onClick={() => setShowAll(!showAll)} className="mt-3 text-xs font-semibold text-blue-700 inline-flex items-center gap-1">
                  {showAll ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />} {showAll ? 'Hide' : 'Show'} all 41 diseases
                </button>
                {showAll && (
                  <div className="mt-2 grid sm:grid-cols-2 gap-x-6 gap-y-1 max-h-64 overflow-y-auto text-xs">
                    {result.all_probabilities.map((d, i) => (
                      <div key={d.disease} className="flex justify-between border-b border-slate-50 py-0.5">
                        <span className="text-slate-600">{i + 1}. {d.disease}</span><span className="tabular-nums text-slate-500">{(d.probability * 100).toFixed(2)}%</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className={`mt-4 p-3 rounded-xl text-sm ${result.low_confidence ? 'bg-amber-50 border border-amber-200 text-amber-800' : 'bg-emerald-50 border border-emerald-200 text-emerald-800'}`}>
                  <p className="font-semibold">Confidence: {result.confidence_level} · {result.clinical_status}</p>
                  {result.low_confidence_reasons.length > 0 && <ul className="list-disc pl-5 mt-1 text-xs space-y-0.5">{result.low_confidence_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
                  <p className="text-xs mt-1 opacity-80">Margin {result.margin_delta} · normalised entropy {result.normalized_entropy} · {result.symptom_count} symptoms</p>
                </div>
              </Card>

              {cr && (
                <Card title="Clinical reasoning report" icon={ClipboardList}
                  right={<span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-800 text-white">{cr.conclusion_strength}</span>}>
                  <p className="text-xs text-slate-500">{cr.case_summary}</p>
                  <div className="mt-3 p-3 rounded-xl bg-indigo-50 border border-indigo-100">
                    <p className="text-[11px] font-bold uppercase text-indigo-700 tracking-wide">Conclusion</p>
                    <p className="text-sm text-slate-800 mt-1">{cr.conclusion}</p>
                  </div>

                  <p className="text-xs font-bold text-slate-700 mt-4 mb-2">Differential - evidence for and against</p>
                  <div className="space-y-2">
                    {cr.differential.map((d) => (
                      <div key={d.disease} className="p-3 rounded-lg border border-slate-200 text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <b className="text-slate-800 text-sm">{d.disease}</b>
                          <span className="flex items-center gap-2">
                            <span className="tabular-nums text-slate-500">{d.percentage}%</span>
                            <span className={`px-2 py-0.5 rounded-full font-semibold ${LEVEL_CLS[d.assessment] || LEVEL_CLS.Unlikely}`}>{d.assessment}</span>
                          </span>
                        </div>
                        <div className="grid sm:grid-cols-2 gap-2 mt-1.5">
                          <p className="text-emerald-700"><b>For:</b> {d.supporting_findings.join(', ') || '—'}</p>
                          <p className="text-rose-700"><b>Against / missing:</b> {d.against_or_missing.join(', ') || '—'}</p>
                        </div>
                        <p className="text-slate-500 mt-1">Explains {d.explains_pct}% of findings · confirm with: {d.confirm_with.join('; ')}</p>
                      </div>
                    ))}
                  </div>

                  <p className="text-xs font-bold text-slate-700 mt-4 mb-2 flex items-center gap-1"><ListChecks className="w-3.5 h-3.5" /> Recommended approach</p>
                  <div className="grid md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-rose-50/60 border border-rose-100">
                      <p className="font-bold text-rose-700 mb-1">Immediate</p>
                      <ul className="list-disc pl-4 space-y-0.5 text-slate-700">{cr.recommended_approach.immediate.map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <p className="font-bold text-slate-700 mb-1">Management approach</p>
                      <ul className="list-disc pl-4 space-y-0.5 text-slate-700">{cr.recommended_approach.management.map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                    <div className="p-3 rounded-lg bg-blue-50/60 border border-blue-100 md:col-span-2">
                      <p className="font-bold text-blue-800 mb-1 flex items-center gap-1"><FlaskConical className="w-3.5 h-3.5" /> Investigations</p>
                      <table className="w-full">
                        <tbody>
                          {cr.recommended_approach.investigations.map((t) => (
                            <tr key={t.test} className="border-t border-blue-100 align-top">
                              <td className="py-1 pr-2 text-slate-800">{t.test}</td>
                              <td className="py-1 pr-2 text-slate-500 whitespace-nowrap">{t.priority}</td>
                              <td className="py-1 text-slate-500">for {t.helps_with.join(', ')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <p className="font-bold text-slate-700 mb-1">Referral</p><p className="text-slate-700">{cr.recommended_approach.referral}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-100">
                      <p className="font-bold text-amber-800 mb-1">Safety-net advice</p>
                      <ul className="list-disc pl-4 space-y-0.5 text-slate-700">{cr.recommended_approach.safety_net.map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                  </div>
                  <details className="mt-3 text-xs text-slate-500">
                    <summary className="cursor-pointer font-semibold">Reasoning steps</summary>
                    <ol className="list-decimal pl-5 mt-1 space-y-0.5">{cr.reasoning_steps.map((x, i) => <li key={i}>{x}</li>)}</ol>
                  </details>
                </Card>
              )}

              <div className="grid md:grid-cols-2 gap-6">
                <Card title="Kernel SHAP explanation" icon={Sparkles}>
                  <p className="text-xs text-slate-500 mb-3">{result.explanation_text}</p>
                  {shapData.length > 0 ? (
                    <div style={{ height: Math.max(160, shapData.length * 28) }}>
                      <ResponsiveContainer>
                        <BarChart data={shapData} layout="vertical" margin={{ left: 10, right: 16 }}>
                          <XAxis type="number" tick={{ fontSize: 10 }} />
                          <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10 }} />
                          <ReferenceLine x={0} stroke="#94a3b8" />
                          <Tooltip formatter={(v) => [`${v > 0 ? '+' : ''}${v}`, 'SHAP (Δ probability)']} />
                          <Bar dataKey="value" radius={[0, 4, 4, 0]}>{shapData.map((d, i) => <Cell key={i} fill={d.value >= 0 ? '#2563eb' : '#f43f5e'} />)}</Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : <p className="text-xs text-slate-400">No attribution available.</p>}
                  <p className="text-[11px] text-slate-400 mt-2">{result.shap_attribution.method}; output = {result.shap_attribution.explained_output}. "(absent)" = the symptom's absence moved the probability.</p>
                </Card>

                <Card title="Ask next" icon={HelpCircle}>
                  <p className="text-xs text-slate-500 mb-3">Symptoms that would best separate the top candidates:</p>
                  <div className="space-y-2">
                    {result.follow_up_questions.map((q) => (
                      <div key={q.symptom} className="flex items-center justify-between gap-2 p-2.5 rounded-lg border border-slate-200">
                        <div><p className="text-sm text-slate-700">{cap(q.symptom)}?</p><p className="text-[11px] text-slate-400">If yes → favours {q.if_yes_favours}</p></div>
                        <button onClick={() => addFollowUp(q.symptom)} className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100"><Plus className="w-3 h-3" /> Add</button>
                      </div>
                    ))}
                    {result.follow_up_questions.length === 0 && <p className="text-xs text-slate-400">No further questions.</p>}
                  </div>
                </Card>
              </div>

              <Card title="Clinician feedback - confirm the final diagnosis" icon={GraduationCap}>
                <p className="text-xs text-slate-500 mb-3">
                  Confirmed cases are stored. After every {info?.real_cases?.retrain_every ?? 5} confirmed cases the MLP is retrained on D1 + confirmed cases
                  and kept only if accuracy on the D1 test split does not drop.
                </p>
                <div className="grid sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-2">
                    <select className={inputCls} value={confirmed} onChange={(e) => setConfirmed(e.target.value)}>
                      {schema?.diseases.map((d) => <option key={d} value={d}>{d}</option>)}
                      <option value="Other">Other / not in list (not used for training)</option>
                    </select>
                  </div>
                  <button onClick={sendFeedback} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700"><CheckCircle2 className="w-4 h-4" /> Confirm diagnosis</button>
                  <input className={`${inputCls} sm:col-span-3`} placeholder="Notes (optional, e.g. confirmed by NS1 test)" value={notes} onChange={(e) => setNotes(e.target.value)} />
                </div>
              </Card>
              <p className="text-[11px] text-slate-400">{result.disclaimer}</p>
            </>
          )}
          {feedbackMsg && <div className={`p-3 rounded-xl text-sm border ${feedbackMsg.ok ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-700'}`}>{feedbackMsg.text}</div>}
        </div>
      </div>

      {/* ------------------------------------------------ MODEL PANEL */}
      {info && (
        <div className="grid lg:grid-cols-3 gap-6">
          <Card title="Deployed model" icon={Network}
            right={<button onClick={retrainNow} disabled={retraining || info.retrain_status.running}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-white hover:bg-slate-900 disabled:opacity-50">
              <RefreshCw className={`w-3.5 h-3.5 ${retraining || info.retrain_status.running ? 'animate-spin' : ''}`} />{retraining || info.retrain_status.running ? 'Training…' : 'Retrain now'}</button>}>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Architecture', info.architecture.layers.join(' → ')],
                ['Parameters', info.architecture.parameters.toLocaleString()],
                ['CV macro-F1', rs?.cv_macro_f1?.toFixed(3) ?? '—'],
                ['CV log-loss', rs?.cv_log_loss?.toFixed(3) ?? '—'],
                ['Test accuracy', info.benchmark ? `${(info.benchmark.accuracy * 100).toFixed(1)}%` : '—'],
                ['Test ECE', rs?.test ? rs.test.ece.toFixed(4) : '—'],
                ['25% symptoms missing', rs?.robustness ? `${(rs.robustness.drop_25pct.accuracy * 100).toFixed(1)}%` : '—'],
                ['50% symptoms missing', rs?.robustness ? `${(rs.robustness.drop_50pct.accuracy * 100).toFixed(1)}%` : '—'],
                ['Confirmed cases', info.real_cases.confirmed],
                ['Waiting to learn', `${info.real_cases.pending_for_training} / ${info.real_cases.retrain_every}`],
              ].map(([k, v]) => (
                <div key={k} className="p-2.5 rounded-lg bg-slate-50"><dt className="text-[10px] uppercase font-semibold text-slate-400 tracking-wide">{k}</dt><dd className="font-bold text-slate-800 text-sm mt-0.5">{v}</dd></div>
              ))}
            </dl>
            <p className="text-[11px] text-slate-400 mt-3">{info.architecture.activation} · {info.architecture.optimizer} · {info.architecture.regularisation}. Selected by: {info.architecture.selected_by}.</p>
            {info.retrain_status.last_message && <p className="text-xs text-slate-600 mt-2 p-2 rounded-lg bg-indigo-50 border border-indigo-100">{info.retrain_status.last_message}</p>}
          </Card>

          <Card title="Versions & training" icon={History} className="lg:col-span-2">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1">D1 test accuracy per version</p>
                <div className="h-44"><ResponsiveContainer>
                  <LineChart data={versionData} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" /><XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis domain={['dataMin - 2', 100]} tick={{ fontSize: 10 }} unit="%" /><Tooltip />
                    <Line type="monotone" dataKey="accuracy" stroke="#2563eb" strokeWidth={2} dot />
                  </LineChart></ResponsiveContainer></div>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1">MLP training loss (current version)</p>
                <div className="h-44"><ResponsiveContainer>
                  <LineChart data={curveData} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" /><XAxis dataKey="epoch" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} /><Tooltip />
                    <Line type="monotone" dataKey="loss" stroke="#6366f1" strokeWidth={2} dot={false} />
                  </LineChart></ResponsiveContainer></div>
              </div>
            </div>
            <div className="mt-3 max-h-36 overflow-y-auto">
              <table className="w-full text-xs"><thead className="text-slate-400 text-left"><tr><th className="py-1">When</th><th>Run</th><th>Result</th></tr></thead>
                <tbody>{[...info.history].reverse().map((h, i) => (
                  <tr key={i} className="border-t border-slate-100 align-top">
                    <td className="py-1.5 pr-2 text-slate-500 whitespace-nowrap">{h.timestamp?.replace('T', ' ')}</td>
                    <td className="pr-2 whitespace-nowrap"><span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${h.accepted ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{h.kind}{h.version ? ` v${h.version}` : ''}</span></td>
                    <td className="text-slate-600">{h.message}</td>
                  </tr>))}</tbody></table>
            </div>
          </Card>

          <Card title="What the model relies on (Kernel SHAP per disease)" icon={Brain} className="lg:col-span-2"
            right={<select className="text-xs border border-slate-200 rounded-md px-2 py-1" value={patternDisease} onChange={(e) => setPatternDisease(e.target.value)}>
              {schema?.diseases.map((d) => <option key={d}>{d}</option>)}</select>}>
            {pattern?.top_features ? (
              <>
                <p className="text-xs text-slate-500 mb-2">Mean SHAP over the {pattern.patterns} D1 patterns of <b>{pattern.disease}</b> (correct on {(pattern.accuracy_on_benchmark * 100).toFixed(0)}% of them).</p>
                <div className="h-56"><ResponsiveContainer>
                  <BarChart data={pattern.top_features.map((f) => ({ name: f.label, value: f.importance, freq: f.frequency_in_d1 }))} layout="vertical" margin={{ left: 10, right: 16 }}>
                    <XAxis type="number" tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v, n, it) => [`${v} (present in ${Math.round(it.payload.freq * 100)}% of patterns)`, 'mean SHAP']} />
                    <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart></ResponsiveContainer></div>
              </>
            ) : <p className="text-xs text-slate-400">Computing Kernel SHAP…</p>}
          </Card>

          <Card title="Recent AI cases" icon={History}>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {cases.map((c) => (
                <div key={c.id} className="p-2.5 rounded-lg border border-slate-100 text-xs">
                  <div className="flex justify-between"><b className="text-slate-700">#{c.id} {c.patient_name || ''}</b><span className="text-slate-400">v{c.model_version ?? '—'}</span></div>
                  <p className="text-slate-600 mt-0.5">AI: {c.predicted || '—'} {c.confidence != null && `(${(c.confidence * 100).toFixed(0)}%)`}</p>
                  {c.confirmed_diagnosis
                    ? <p className={c.confirmed_diagnosis === c.predicted ? 'text-emerald-600' : 'text-amber-600'}>Confirmed: {c.confirmed_diagnosis} {c.used_in_version ? `· learned in v${c.used_in_version}` : '· waiting'}</p>
                    : <p className="text-slate-400">Not confirmed</p>}
                </div>
              ))}
              {cases.length === 0 && <p className="text-xs text-slate-400">No cases yet.</p>}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
