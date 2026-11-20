import React, { useEffect, useState } from 'react'
import api from '../api/axios'
import { FlaskConical, Database, Brain, CalendarClock, UserX, AlertTriangle, Image as ImageIcon } from 'lucide-react'

const pct = (v, d = 2) => (v == null ? '—' : `${(v * 100).toFixed(d)}%`)
const num = (v, d = 3) => (v == null ? '—' : Number(v).toFixed(d))

function Section({ title, icon: Icon, children, note }) {
  return (
    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm">
      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between gap-2">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2"><Icon className="w-4 h-4 text-blue-600" /> {title}</h2>
        {note && <span className="text-[11px] text-slate-400">{note}</span>}
      </div>
      <div className="p-5 overflow-x-auto">{children}</div>
    </section>
  )
}

function Fig({ name, caption }) {
  const src = `${api.defaults.baseURL}/api/research/figures/${name}`
  return (
    <figure className="border border-slate-100 rounded-xl p-2 bg-slate-50/50">
      <img src={src} alt={caption} className="w-full rounded-lg" loading="lazy" />
      <figcaption className="text-[11px] text-slate-500 mt-1 px-1">{caption}</figcaption>
    </figure>
  )
}

const th = 'py-2 px-3 text-left text-[11px] uppercase tracking-wide text-slate-400 font-semibold whitespace-nowrap'
const td = 'py-2 px-3 text-sm text-slate-700 whitespace-nowrap tabular-nums'

export default function ResearchPage() {
  const [r, setR] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get('/api/research/results').then((x) => setR(x.data)).catch(() => setErr('Could not load research results from the backend.'))
  }, [])
  if (err) return <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm">{err}</div>
  if (!r) return <p className="text-sm text-slate-500">Loading results…</p>
  const d = r.disease, n = r.noshow, s = r.scheduling
  const has = (f) => r.figures?.includes(f)

  return (
    <div className="space-y-6">
      <div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
          <FlaskConical className="w-3.5 h-3.5" /> Computed by backend/research/run_all.py - no hard-coded values
        </span>
        <h1 className="text-2xl font-bold text-slate-800">Research Results</h1>
        <p className="text-sm text-slate-500 mt-0.5">Every number on this page is produced by the experiment pipeline described in the report (Chapters 3-4).</p>
      </div>

      {d && (
        <Section title="Data preparation (D1 / D2)" icon={Database} note={`generated ${d.generated_at?.replace('T', ' ')}`}>
          <ul className="text-sm text-slate-700 space-y-1 list-disc pl-5">
            <li>D1: {d.data.raw_rows} rows, {d.data.raw_symptom_columns} symptom columns, {d.data.diseases} diseases, {d.data.missing_values} missing values.</li>
            <li>Removed column <b>{d.data.removed_columns.join(', ')}</b> ({d.data.removed_columns_reason}).</li>
            <li>{d.data.duplicate_rows_removed} duplicate rows removed before splitting → <b>{d.data.unique_patterns} unique patterns, {d.data.symptom_features} features</b>.</li>
            <li>Testing.csv: {d.data.testing_csv_rows_in_training} of {d.data.testing_csv_rows} rows already in Training.csv → not used.</li>
            <li>D2: {d.data.d2.d2_unique_patterns} unique patterns, {d.data.d2.d2_patterns_matching_d1} match D1 → consistency check only.</li>
            <li>Stratified 80:20 split: {d.split.train} train / {d.split.test} test. 4-fold stratified CV for tuning.</li>
          </ul>
        </Section>
      )}

      {d && (
        <Section title="Disease prediction - model comparison" icon={Brain} note={`selected by CV: ${d.selection.selected} · deployed: ${d.deployed_model}`}>
          <table className="w-full">
            <thead><tr className="border-b border-slate-100">
              {['Model', 'CV macro-F1', 'CV log-loss', 'Test acc.', 'Test macro-F1', 'Log-loss', 'Top-3', 'ECE', '30 splits (mean ± sd)', '25% removed', '50% removed'].map((h) => <th key={h} className={th}>{h}</th>)}
            </tr></thead>
            <tbody>
              {Object.entries(d.models).map(([k, m]) => (
                <tr key={k} className={`border-b border-slate-50 ${k === d.deployed_model ? 'bg-blue-50/50 font-semibold' : ''}`}>
                  <td className={td}>{k}</td><td className={td}>{num(m.cv_macro_f1)}</td><td className={td}>{num(m.cv_log_loss)}</td>
                  <td className={td}>{pct(m.test.accuracy)}</td><td className={td}>{pct(m.test.macro_f1)}</td><td className={td}>{num(m.test.log_loss, 4)}</td>
                  <td className={td}>{pct(m.test.top3_accuracy, 1)}</td><td className={td}>{num(m.test.ece, 4)}</td>
                  <td className={td}>{pct(m.repeated_splits.accuracy.mean)} ± {pct(m.repeated_splits.accuracy.std)}</td>
                  <td className={td}>{pct(m.robustness.drop_25pct.accuracy, 1)}</td><td className={td}>{pct(m.robustness.drop_50pct.accuracy, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-slate-500 mt-3">Selection rule: {d.selection.rule}. Tied candidates: {d.selection.tied_candidates.join(', ')}.</p>
          <p className="text-xs text-amber-700 mt-2 flex gap-1.5"><AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {d.caveat}</p>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            {has('disease_models.png') && <Fig name="disease_models.png" caption="Held-out accuracy and macro-F1" />}
            {has('repeated_splits.png') && <Fig name="repeated_splits.png" caption="30 repeated stratified splits" />}
            {has('robustness.png') && <Fig name="robustness.png" caption="Accuracy when 25% / 50% of positive symptoms are removed" />}
            {has('calibration.png') && <Fig name="calibration.png" caption="Reliability diagram of the deployed MLP" />}
            {has('shap_global.png') && <Fig name="shap_global.png" caption={`Global Kernel SHAP (background ${d.shap.background_size})`} />}
          </div>
        </Section>
      )}

      <Section title="No-show prediction (D3)" icon={UserX}>
        {n?.status === 'ok' ? (
          <>
            <p className="text-sm text-slate-600 mb-3">{n.data.valid_records} valid records, no-show rate {pct(n.data.no_show_rate, 1)}, patient-wise split {n.data.train_records} / {n.data.test_records}. Selected: <b>{n.selected}</b> ({n.selection_rule}).</p>
            <table className="w-full"><thead><tr className="border-b border-slate-100">{['Model', 'CV PR-AUC', 'ROC-AUC', 'PR-AUC', 'Brier', 'Top-20% lift'].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
              <tbody>{Object.entries(n.models).map(([k, m]) => (
                <tr key={k} className="border-b border-slate-50"><td className={td}>{k}</td><td className={td}>{num(m.cv_pr_auc)}</td><td className={td}>{pct(m.test.roc_auc)}</td>
                  <td className={td}>{pct(m.test.pr_auc)}</td><td className={td}>{num(m.test.brier)}</td><td className={td}>{num(m.test.lift_top20, 2)}×</td></tr>))}</tbody></table>
            {has('noshow_models.png') && <div className="max-w-lg mt-4"><Fig name="noshow_models.png" caption="No-show models on the patient-wise test split" /></div>}
          </>
        ) : (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-800">
            Not trained yet. Download Kaggle <b>Medical Appointment No Shows</b> (<code>KaggleV2-May-2016.csv</code>), place it in <code>backend/data/d3/</code> and run <code>python -m research.run_all</code>.
          </div>
        )}
      </Section>

      {s && (
        <Section title="Appointment scheduling simulation" icon={CalendarClock} note={`${s.config.seeds} seeds · ${s.config.warmup_days}+${s.config.measured_days} days · ${s.config.doctors} doctors`}>
          <table className="w-full">
            <thead><tr className="border-b border-slate-100"><th className={th}>Metric (normal demand)</th><th className={th}>FCFS</th><th className={th}>Fixed 30-min</th><th className={th}>Proposed</th></tr></thead>
            <tbody>
              {[['Mean wait from request (days)', 'mean_wait_days', 2], ['Wait beyond preferred date (days)', 'mean_excess_wait_days', 2], ['Urgent wait (days)', 'urgent_wait_days', 2],
                ['High-priority wait (days)', 'high_wait_days', 2], ['Urgent seen within 1 day (%)', 'urgent_within_1_day_pct', 1], ['Preference satisfaction (%)', 'preference_satisfaction_pct', 1],
                ['Schedule completion (%)', 'scheduled_pct', 1], ['Doctor utilisation (%)', 'doctor_utilization_pct', 1]].map(([t, k, dp]) => (
                <tr key={k} className="border-b border-slate-50"><td className={td}>{t}</td>
                  {['fcfs', 'fixed', 'proposed'].map((p) => <td key={p} className={`${td} ${p === 'proposed' ? 'font-semibold text-blue-700' : ''}`}>{s.summary['1.0'][p][k].mean.toFixed(dp)} <span className="text-slate-400 text-xs">± {s.summary['1.0'][p][k].std.toFixed(dp)}</span></td>)}</tr>
              ))}
              <tr><td className={td}>Constraint violations (all runs)</td>{['fcfs', 'fixed', 'proposed'].map((p) => <td key={p} className={td}>{s.constraint_violations[p]}</td>)}</tr>
            </tbody>
          </table>
          <div className="grid sm:grid-cols-3 gap-3 mt-4 text-sm">
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100"><p className="text-xs text-emerald-700 font-semibold">Urgent wait vs FCFS</p><p className="text-xl font-bold text-emerald-700">-{s.headline.urgent_wait_reduction_pct_vs_fcfs.toFixed(1)}%</p></div>
            <div className="p-3 rounded-xl bg-blue-50 border border-blue-100"><p className="text-xs text-blue-700 font-semibold">Urgent seen within 1 day</p><p className="text-xl font-bold text-blue-700">{s.headline.urgent_within_1_day_fcfs.toFixed(1)}% → {s.headline.urgent_within_1_day_proposed.toFixed(1)}%</p></div>
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-100"><p className="text-xs text-amber-700 font-semibold">Rescheduling delay after 7-day absence</p><p className="text-xl font-bold text-amber-700">{s.physician_absence.fixed.mean_delay_days.toFixed(2)}d → {s.physician_absence.proposed.mean_delay_days.toFixed(2)}d</p></div>
          </div>
          <p className="text-xs text-slate-500 mt-3">Trade-off: the proposed policy books routine patients on their preferred (later) dates and moves capacity to urgent patients, so mean wait from request is higher than FCFS while urgent wait falls sharply.</p>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            {has('scheduling_baseline.png') && <Fig name="scheduling_baseline.png" caption="Policies at normal demand (mean ± sd over 20 seeds)" />}
            {has('scheduling_demand.png') && <Fig name="scheduling_demand.png" caption="Urgent wait across demand levels" />}
          </div>
        </Section>
      )}
      {!d && !s && <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-800 flex gap-2"><ImageIcon className="w-4 h-4" /> No results yet - run <code>python -m research.run_all</code> in backend/.</div>}
    </div>
  )
}
