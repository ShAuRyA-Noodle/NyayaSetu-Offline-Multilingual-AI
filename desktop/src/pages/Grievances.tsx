import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, Send, CheckCircle, Clock, MessageSquare, Star, ChevronDown, ChevronUp, User, Check, X, Inbox, Briefcase, Mic, RotateCcw, Edit3, Info, Printer } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import FileAttachment from '../components/ui/FileAttachment';
import toast from 'react-hot-toast';
import apiService from '../services/api';
import VoiceInputButton from '../components/nyayavaani/VoiceInputButton';

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.07, duration: 0.35, ease: 'easeOut' as const },
  }),
};

const Grievances: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const role = user?.role || 'citizen';

  const getTabs = () => {
    if (role === 'admin') return [
      { id: 'all', label: t('grievances.allTab', 'All Grievances') },
      { id: 'analytics', label: t('grievances.analyticsTab', 'Analytics') },
    ];
    if (role === 'officer') return [
      { id: 'inbox', label: t('grievances.deptInboxTab', 'Department Inbox') },
      { id: 'mycases', label: t('grievances.myCasesTab', 'My Cases') },
      { id: 'submit', label: t('grievances.submitTab', 'Submit New') },
    ];
    return [
      { id: 'submit', label: t('grievances.submitTab', 'Submit') },
      { id: 'my', label: t('grievances.myGrievancesTab', 'My Grievances') },
    ];
  };

  const tabs = getTabs();
  const [activeTab, setActiveTab] = useState(tabs[0].id);

  return (
    <PageTransition>
      <div className="p-4 md:p-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="mb-6"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h1 className="text-2xl md:text-3xl font-bold text-kora-100 tracking-tight mb-2">{t('grievances.title', 'Grievances')}</h1>
            <p className="text-sm text-mitti-500/40">
              {role === 'admin'
                ? t('grievances.adminSubtitle', 'Monitor all grievances system-wide')
                : role === 'officer'
                ? t('grievances.officerSubtitle', 'Manage department grievances')
                : t('grievances.citizenSubtitle', 'Submit and track your grievances')}
            </p>
          </motion.div>

          <div className="flex space-x-2 mb-6 village-card p-2 rounded-xl inline-flex flex-wrap">
            {tabs.map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2 rounded-lg font-medium transition-all ${activeTab === tab.id ? 'bg-[#0D92F4] text-white shadow-lg' : 'text-mitti-600 dark:text-mitti-400 hover:bg-mitti-100/50 dark:hover:bg-night-card/50'}`}>
                {tab.label}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {activeTab === 'submit' && <motion.div key="submit" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><SubmitTab /></motion.div>}
            {activeTab === 'my' && <motion.div key="my" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><MyGrievancesTab /></motion.div>}
            {activeTab === 'inbox' && <motion.div key="inbox" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><DepartmentInboxTab /></motion.div>}
            {activeTab === 'mycases' && <motion.div key="mycases" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><MyCasesTab /></motion.div>}
            {activeTab === 'all' && <motion.div key="all" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><AllGrievancesTab /></motion.div>}
            {activeTab === 'analytics' && <motion.div key="analytics" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><AnalyticsTab /></motion.div>}
          </AnimatePresence>
        </div>
      </div>
    </PageTransition>
  );
};

/* ===================== SUBMIT TAB ===================== */

const EMPTY_FORM = {
  title: '', description: '', category: '', language: 'en',
  citizen_name: '', citizen_phone: '', citizen_email: '', citizen_location: ''
};

const SubmitTab: React.FC = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({ ...EMPTY_FORM });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  // Voice fill tracking: which fields were populated by voice (for visual indicator)
  const [voiceFilled, setVoiceFilled] = useState<{ title?: boolean; description?: boolean; language?: boolean } | null>(null);
  const [attachments, setAttachments] = useState<File[]>([]);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const categories = [
    { value: 'payment_delay', label: t('grievances.categories.paymentDelay', 'Payment Delays') },
    { value: 'eligibility_query', label: t('grievances.categories.eligibility', 'Eligibility Questions') },
    { value: 'service_denial', label: t('grievances.categories.serviceDenial', 'Service Denial') },
    { value: 'documentation_issue', label: t('grievances.categories.documentation', 'Document Issues') },
    { value: 'application_rejection', label: t('grievances.categories.applicationRejection', 'Application Rejection') },
    { value: 'corruption', label: t('grievances.categories.corruption', 'Corruption / Misconduct') },
    { value: 'infrastructure_complaint', label: t('grievances.categories.infrastructure', 'Infrastructure Issues') },
    { value: 'other', label: t('grievances.categories.other', 'Other Issues') },
  ];

  // Validate required fields before submit
  const isValid = formData.description.trim().length >= 10;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Guard: never submit without explicit user click on button
    if (!isValid || isSubmitting) return;
    setIsSubmitting(true);
    setResult(null);
    setVoiceFilled(null);
    try {
      const payload = {
        description: formData.description.trim(),
        title: formData.title.trim() || undefined,
        citizen_name: formData.citizen_name.trim() || undefined,
        citizen_phone: formData.citizen_phone.trim() || undefined,
        citizen_email: formData.citizen_email.trim() || undefined,
        citizen_location: formData.citizen_location.trim() || undefined,
        category: formData.category || undefined,
        language: formData.language,
      };

      let response: any;
      if (attachments.length > 0) {
        // Multipart upload — use raw axios client until api.ts adds a typed helper.
        // TODO(api.ts agent): add `submitGrievanceWithFiles(data: SubmitGrievanceData, files: File[])`
        // that posts multipart/form-data to POST /api/v1/grievances/submit.
        const fd = new FormData();
        Object.entries(payload).forEach(([k, v]) => {
          if (v !== undefined && v !== null) fd.append(k, String(v));
        });
        attachments.forEach((f) => fd.append('attachments', f, f.name));
        const res = await apiService.client.post('/api/v1/grievances/submit', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 120000,
        });
        response = res.data;
      } else {
        response = await apiService.submitGrievance(payload);
      }

      // Stash the submitted form so the receipt can render after we reset state.
      setResult({ ...response, _submitted: { ...payload, submitted_at: new Date().toISOString() } });
      // Reset form on success
      setFormData({ ...EMPTY_FORM });
      setAttachments([]);
    } catch {
      setResult({ error: t('grievances.submitError', 'Failed to submit grievance. Please try again.') });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePrintReceipt = () => {
    // Toggle a body class so print CSS shows only the receipt; revert after.
    document.body.classList.add('printing-receipt');
    const cleanup = () => document.body.classList.remove('printing-receipt');
    window.addEventListener('afterprint', cleanup, { once: true });
    setTimeout(() => {
      window.print();
      // Fallback for browsers that do not fire afterprint.
      setTimeout(cleanup, 1500);
    }, 50);
  };

  const handleVoiceTranscription = (text: string, lang: string) => {
    // Append transcription to existing description (never replace — user may have typed something)
    const newDesc = formData.description
      ? formData.description.trim() + ' ' + text.trim()
      : text.trim();

    const updates: Partial<typeof EMPTY_FORM> = { description: newDesc };
    const filled: typeof voiceFilled = { description: true };

    // Auto-set language from detected language
    const detectedLang = lang?.toLowerCase();
    if (detectedLang && detectedLang !== 'auto') {
      const langMap: Record<string, string> = {
        hi: 'hi', hindi: 'hi', hin: 'hi',
        en: 'en', english: 'en', eng: 'en',
      };
      const mapped = langMap[detectedLang];
      if (mapped && mapped !== formData.language) {
        updates.language = mapped;
        filled.language = true;
      }
    }

    // Auto-generate title from first sentence only if title is currently empty
    if (!formData.title.trim() && text.trim().length > 15) {
      const firstSentence = text.trim().split(/[।.!?\n]/)[0]?.trim();
      if (firstSentence && firstSentence.length > 5) {
        updates.title = firstSentence.slice(0, 80);
        filled.title = true;
      }
    }

    // Only update state — NEVER call handleSubmit here
    setFormData(prev => ({ ...prev, ...updates }));
    setVoiceFilled(filled);

    // Scroll to description so user can review
    setTimeout(() => {
      descriptionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      descriptionRef.current?.focus();
    }, 300);
  };

  const handleClearVoiceBanner = () => setVoiceFilled(null);

  const handleResetForm = () => {
    setFormData({ ...EMPTY_FORM });
    setResult(null);
    setVoiceFilled(null);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <motion.div className="lg:col-span-2" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <form ref={formRef} onSubmit={handleSubmit} className="village-card rounded-xl p-6 space-y-5">
          {/* Form header with reset button */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-kora-100">File a Grievance</h2>
              <p className="text-xs text-slate-500 mt-0.5">All fields with * are required. Review before submitting.</p>
            </div>
            {(formData.description || formData.title) && (
              <button type="button" onClick={handleResetForm}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded-lg hover:bg-white/[0.04]">
                <RotateCcw className="w-3.5 h-3.5" />
                Clear form
              </button>
            )}
          </div>

          {/* Voice fill success banner */}
          <AnimatePresence>
            {voiceFilled && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <div className="rounded-xl border border-[#0D92F4]/20 bg-[#0D92F4]/[0.06] px-4 py-3 flex items-start gap-3">
                  <div className="mt-0.5 w-5 h-5 rounded-full bg-[#0D92F4]/20 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-[#0D92F4]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#77CDFF]">Voice transcription added to form</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Filled:{' '}
                      {[
                        voiceFilled.description && 'Description',
                        voiceFilled.title && 'Title (from first sentence)',
                        voiceFilled.language && 'Language (auto-detected)',
                      ].filter(Boolean).join(' · ')}
                    </p>
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                      <Edit3 className="w-3 h-3" />
                      Review and edit the fields below before submitting
                    </p>
                  </div>
                  <button type="button" onClick={handleClearVoiceBanner} className="text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Language selector */}
          <div>
            <label className="block text-sm font-medium text-kora-300/70 mb-2">Response Language</label>
            <div className="flex space-x-3">
              {[{ val: 'en', label: 'English' }, { val: 'hi', label: 'Hindi' }].map(l => (
                <button key={l.val} type="button" onClick={() => setFormData(prev => ({ ...prev, language: l.val }))}
                  className={`flex-1 py-2 rounded-lg font-medium transition-all text-sm ${formData.language === l.val ? 'bg-[#0D92F4] text-white shadow-lg shadow-[#0D92F4]/20' : 'bg-white/[0.04] text-slate-400 hover:bg-white/[0.08]'}`}>
                  {l.label}
                  {formData.language === l.val && voiceFilled?.language && (
                    <span className="ml-1.5 text-[10px] opacity-70">(auto-detected)</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-kora-300/70 mb-2">Category</label>
            <select value={formData.category} onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
              className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30">
              <option value="">Select category...</option>
              {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>

          {/* Title */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-kora-300/70">
                Title
                {voiceFilled?.title && (
                  <span className="ml-2 text-[10px] text-[#0D92F4] font-normal">(filled by voice — editable)</span>
                )}
              </label>
              <span className="text-[11px] text-slate-500">{formData.title.length}/80</span>
            </div>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value.slice(0, 80) }))}
              placeholder="Brief summary of your complaint..."
              className={`village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30 transition-all ${voiceFilled?.title ? 'ring-1 ring-[#0D92F4]/30' : ''}`}
            />
          </div>

          {/* Voice Input */}
          <div className="rounded-xl border border-[#0D92F4]/10 bg-[#0D92F4]/[0.03] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Mic className="w-3.5 h-3.5 text-[#0D92F4]" />
              <span className="text-xs font-semibold text-[#77CDFF] uppercase tracking-wider">Speak Your Complaint</span>
              <span className="text-[10px] text-slate-500 ml-auto">12 Indian languages supported</span>
            </div>
            <div className="flex items-center gap-4">
              <VoiceInputButton
                onTranscription={handleVoiceTranscription}
                size="md"
                label="Tap to speak"
                languageHint={formData.language}
              />
              <div className="flex-1 min-w-0 space-y-1">
                <p className="text-xs text-slate-400 leading-relaxed">
                  Speak in Hindi, English, Tamil, Telugu, Bengali, or any of 12 Indian languages. Transcription fills the form — you review and edit before submitting.
                </p>
                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                  <Info className="w-3 h-3" />
                  <span>Voice never auto-submits — always requires your manual confirmation</span>
                </div>
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-kora-300/70">
                Description *
                {voiceFilled?.description && (
                  <span className="ml-2 text-[10px] text-[#0D92F4] font-normal">(filled by voice — editable)</span>
                )}
              </label>
              <span className={`text-[11px] tabular-nums ${formData.description.trim().length >= 10 ? 'text-[#0D92F4]' : 'text-slate-500'}`}>
                {formData.description.length} chars {formData.description.trim().length < 10 && formData.description.length > 0 ? '(min 10)' : ''}
              </span>
            </div>
            <textarea
              ref={descriptionRef}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe your issue in detail — what happened, where, when, and what outcome you expect. Or use voice input above."
              rows={6}
              required
              className={`village-input w-full px-3 py-2 rounded-lg text-kora-100 resize-none transition-all ${voiceFilled?.description ? 'ring-1 ring-[#0D92F4]/30' : ''}`}
            />
            {formData.description.trim().length > 0 && formData.description.trim().length < 10 && (
              <p className="text-xs text-[#F95454] mt-1">Please provide at least 10 characters</p>
            )}
          </div>

          {/* Contact details */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-px flex-1 bg-white/[0.06]" />
              <span className="text-xs text-slate-500 px-2">Contact Details (optional)</span>
              <div className="h-px flex-1 bg-white/[0.06]" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-kora-300/60 mb-1">Full Name</label>
                <input type="text" value={formData.citizen_name} onChange={(e) => setFormData(prev => ({ ...prev, citizen_name: e.target.value }))}
                  placeholder="Your name"
                  className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-kora-300/60 mb-1">Phone Number</label>
                <input type="tel" value={formData.citizen_phone} onChange={(e) => setFormData(prev => ({ ...prev, citizen_phone: e.target.value }))}
                  placeholder="+91 XXXXX XXXXX"
                  className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-kora-300/60 mb-1">Email Address</label>
                <input type="email" value={formData.citizen_email} onChange={(e) => setFormData(prev => ({ ...prev, citizen_email: e.target.value }))}
                  placeholder="you@example.com"
                  className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-kora-300/60 mb-1">Location / District</label>
                <input type="text" value={formData.citizen_location} onChange={(e) => setFormData(prev => ({ ...prev, citizen_location: e.target.value }))}
                  placeholder="City, State"
                  className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30 text-sm" />
              </div>
            </div>
          </div>

          {/* File attachments */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-px flex-1 bg-white/[0.06]" />
              <span className="text-xs text-slate-500 px-2">Attachments (optional)</span>
              <div className="h-px flex-1 bg-white/[0.06]" />
            </div>
            <FileAttachment
              files={attachments}
              onChange={setAttachments}
              accept="image/*,application/pdf"
              maxFiles={3}
              maxSize={10 * 1024 * 1024}
              disabled={isSubmitting}
            />
          </div>

          {/* Review checklist before submit */}
          {isValid && !result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 space-y-1.5"
            >
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Before you submit — review:</p>
              {[
                { label: 'Description is accurate and complete', done: formData.description.trim().length >= 10 },
                { label: 'Title reflects the issue', done: !!formData.title.trim() },
                { label: 'Category selected', done: !!formData.category },
                { label: 'Language is correct', done: true },
              ].map(({ label, done }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center flex-shrink-0 ${done ? 'bg-[#0D92F4]/20' : 'bg-white/[0.04]'}`}>
                    {done ? <Check className="w-2.5 h-2.5 text-[#0D92F4]" /> : <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />}
                  </div>
                  <span className={`text-xs ${done ? 'text-slate-300' : 'text-slate-500'}`}>{label}</span>
                </div>
              ))}
            </motion.div>
          )}

          {/* Submit — explicit, prominent, disabled when invalid */}
          <button
            type="submit"
            disabled={!isValid || isSubmitting}
            className="btn-mitti w-full py-3.5 rounded-xl font-semibold transition-all text-white hover:shadow-lg hover:shadow-[#0D92F4]/20 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
          >
            {isSubmitting ? (
              <><ThemedSpinner size="sm" /><span>Submitting grievance...</span></>
            ) : (
              <><Send className="w-4 h-4" /><span>Submit Grievance</span></>
            )}
          </button>
          {!isValid && formData.description.length === 0 && (
            <p className="text-xs text-center text-slate-500 -mt-2">Fill in the description to enable submission</p>
          )}
        </form>
      </motion.div>

      {/* Result panel */}
      <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
        <div className="village-card rounded-xl p-6 sticky top-6">
          <h3 className="text-base font-semibold text-kora-100 mb-4">Submission Result</h3>
          {!result && !isSubmitting && (
            <div className="text-center py-10">
              <div className="w-14 h-14 rounded-full bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-3">
                <Send className="w-6 h-6 text-slate-600" />
              </div>
              <p className="text-sm text-slate-500">Fill the form and click Submit to see AI routing results</p>
              <p className="text-xs text-slate-600 mt-2">Your grievance will be automatically routed to the relevant department</p>
            </div>
          )}
          {isSubmitting && (
            <div className="text-center py-10">
              <ThemedSpinner size="lg" className="mx-auto mb-4" />
              <p className="text-sm text-slate-400">Analyzing and routing your grievance...</p>
              <p className="text-xs text-slate-500 mt-1">This takes a few seconds</p>
            </div>
          )}
          {result && !result.error && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl border border-green-500/20 bg-green-500/[0.06]">
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-semibold text-green-400">Submitted Successfully</span>
                </div>
                {result.grievance_id && (
                  <p className="font-mono text-base font-bold text-green-300 mt-1">{result.grievance_id}</p>
                )}
                <p className="text-xs text-slate-500 mt-1">Save this ID to track your grievance</p>
              </div>
              {result.department && (
                <div className="p-3 rounded-xl border border-[#77CDFF]/15 bg-[#0D92F4]/[0.05]">
                  <p className="text-[10px] text-[#77CDFF] font-semibold uppercase tracking-wider mb-1">Routed To</p>
                  <p className="font-semibold text-kora-100">{result.department}</p>
                </div>
              )}
              {result.priority && (
                <div className="p-3 rounded-xl border border-orange-500/15 bg-orange-500/[0.05]">
                  <p className="text-[10px] text-orange-400 font-semibold uppercase tracking-wider mb-1">Priority</p>
                  <p className="font-semibold text-orange-300 capitalize">{result.priority}</p>
                </div>
              )}
              {result.routing_reasoning && (
                <div className="p-3 rounded-xl border border-white/[0.06] bg-white/[0.02]">
                  <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">AI Reasoning</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{result.routing_reasoning}</p>
                </div>
              )}

              {/* Print / download receipt */}
              <button
                type="button"
                onClick={handlePrintReceipt}
                className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm font-medium text-kora-100 hover:bg-white/[0.06] transition-colors"
              >
                <Printer className="w-4 h-4" />
                Download receipt (PDF)
              </button>
              <p className="text-[11px] text-slate-500 text-center -mt-1.5">
                Opens the print dialog — choose &ldquo;Save as PDF&rdquo;.
              </p>
            </div>
          )}
          {result?.error && (
            <div className="p-3 rounded-xl border border-[#F95454]/20 bg-[#F95454]/[0.06]">
              <p className="text-xs font-semibold text-[#F95454] mb-1">Submission Failed</p>
              <p className="text-sm text-slate-400">{result.error}</p>
              <button type="button" onClick={() => setResult(null)}
                className="text-xs text-[#0D92F4] mt-2 hover:underline">Try again</button>
            </div>
          )}
        </div>
      </motion.div>

      {/* ───── Hidden printable receipt — only visible when body has .printing-receipt ───── */}
      {result && !result.error && (
        <div id="grievance-receipt" className="grievance-receipt-print" aria-hidden="true">
          <style>{`
            /* Hidden by default. The print stylesheet is applied via @media print
               below; on screen we keep this fully off-canvas. */
            .grievance-receipt-print {
              position: fixed; left: -10000px; top: 0; width: 0; height: 0; overflow: hidden;
            }
            @media print {
              body.printing-receipt > *:not(.grievance-receipt-print) { display: none !important; }
              body.printing-receipt .grievance-receipt-print {
                position: static !important; left: auto !important; top: auto !important;
                width: auto !important; height: auto !important; overflow: visible !important;
                color: #000; background: #fff; padding: 24pt; font-family: Inter, system-ui, sans-serif;
                font-size: 11pt; line-height: 1.5;
              }
              body.printing-receipt .gr-r-title { font-size: 18pt; font-weight: 700; margin-bottom: 4pt; }
              body.printing-receipt .gr-r-sub { font-size: 10pt; color: #444; margin-bottom: 16pt; }
              body.printing-receipt .gr-r-row { display: flex; gap: 12pt; margin-bottom: 6pt; }
              body.printing-receipt .gr-r-label { width: 130pt; color: #555; font-weight: 600; font-size: 9.5pt; text-transform: uppercase; letter-spacing: 0.04em; }
              body.printing-receipt .gr-r-value { flex: 1; }
              body.printing-receipt .gr-r-id { font-family: ui-monospace, Menlo, monospace; font-size: 14pt; font-weight: 700; }
              body.printing-receipt .gr-r-divider { border-top: 1px solid #ccc; margin: 16pt 0; }
              body.printing-receipt .gr-r-footer { margin-top: 24pt; font-size: 9pt; color: #666; border-top: 1px solid #ccc; padding-top: 12pt; }
            }
          `}</style>
          <h1 className="gr-r-title">NyayaSetu — Grievance Receipt</h1>
          <p className="gr-r-sub">न्यायसेतु · Official acknowledgement of filing</p>

          <div className="gr-r-row">
            <span className="gr-r-label">Grievance ID</span>
            <span className="gr-r-value gr-r-id">{result.grievance_id || '—'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Submitted on</span>
            <span className="gr-r-value">
              {result._submitted?.submitted_at
                ? new Date(result._submitted.submitted_at).toLocaleString()
                : new Date().toLocaleString()}
            </span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Citizen name</span>
            <span className="gr-r-value">{result._submitted?.citizen_name || '—'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Phone</span>
            <span className="gr-r-value">{result._submitted?.citizen_phone || '—'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Location</span>
            <span className="gr-r-value">{result._submitted?.citizen_location || '—'}</span>
          </div>

          <div className="gr-r-divider" />

          <div className="gr-r-row">
            <span className="gr-r-label">Department</span>
            <span className="gr-r-value">{result.department || 'Pending assignment'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Status</span>
            <span className="gr-r-value">{(result.status || 'pending').toString().toUpperCase()}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Priority</span>
            <span className="gr-r-value" style={{ textTransform: 'capitalize' }}>{result.priority || '—'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Title</span>
            <span className="gr-r-value">{result._submitted?.title || '—'}</span>
          </div>
          <div className="gr-r-row">
            <span className="gr-r-label">Description</span>
            <span className="gr-r-value">{result._submitted?.description || '—'}</span>
          </div>

          <p className="gr-r-footer">
            Keep this receipt for your records. You can track this grievance any time using the ID above.
            For questions, contact the assigned department or write to support@nyayasetu.in.
          </p>
        </div>
      )}
    </div>
  );
};

/* ===================== MY GRIEVANCES TAB (CITIZEN) ===================== */
const LIFECYCLE_STAGES = ['pending', 'accepted', 'in_progress', 'resolved'] as const;
const STAGE_LABELS: Record<string, string> = {
  pending: 'Submitted',
  accepted: 'Accepted',
  in_progress: 'In Progress',
  resolved: 'Resolved',
};

const MyGrievancesTab: React.FC = () => {
  const { t } = useTranslation();
  const [grievances, setGrievances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, any[]>>({});
  const [timelines, setTimelines] = useState<Record<string, any[]>>({});
  const [newComment, setNewComment] = useState('');
  const [ratingModal, setRatingModal] = useState<string | null>(null);
  const [rating, setRating] = useState(3);
  const [feedback, setFeedback] = useState('');
  const [visibleCount, setVisibleCount] = useState(25);
  const PAGE_SIZE = 25;

  useEffect(() => { loadGrievances(); }, []);

  const loadGrievances = async () => {
    setLoading(true);
    try {
      const data = await apiService.getMyGrievances();
      setGrievances(data.grievances || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const loadComments = async (grievanceId: string) => {
    try {
      const data = await apiService.getGrievanceComments(grievanceId);
      setComments(prev => ({ ...prev, [grievanceId]: data.comments || [] }));
    } catch { /* ignore */ }
  };

  const loadTimeline = async (grievanceId: string) => {
    try {
      const data = await apiService.getGrievanceTimeline(grievanceId);
      setTimelines(prev => ({ ...prev, [grievanceId]: data.timeline || [] }));
    } catch { /* ignore */ }
  };

  const handleAddComment = async (grievanceId: string) => {
    if (!newComment.trim()) return;
    try {
      await apiService.addGrievanceComment(grievanceId, newComment, 'note', true);
      setNewComment('');
      loadComments(grievanceId);
    } catch { /* ignore */ }
  };

  const handleRate = async (grievanceId: string) => {
    try {
      await apiService.rateGrievance(grievanceId, rating, feedback || undefined);
      // Update local state immediately so UI reflects the rating
      setGrievances(prev => prev.map(g =>
        g.grievance_id === grievanceId
          ? { ...g, rating: { rating } }
          : g
      ));
      setRatingModal(null);
      setRating(3);
      setFeedback('');
    } catch (err) {
      console.error('Rating submission failed:', err);
    }
  };

  const toggleExpand = (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
      if (!comments[id]) loadComments(id);
      if (!timelines[id]) loadTimeline(id);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      case 'pending': return 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400';
      case 'accepted': return 'bg-mitti-100 text-mitti-600 dark:bg-mitti-800/20 dark:text-mitti-400';
      case 'in_progress': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      case 'rejected': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default: return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'officer': return <span className="px-1.5 py-0.5 bg-mitti-100 dark:bg-mitti-800/20 text-mitti-600 dark:text-mitti-400 text-[10px] font-bold rounded uppercase ml-1.5">{t('grievances.officer', 'Officer')}</span>;
      case 'admin': return <span className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 text-[10px] font-bold rounded uppercase ml-1.5">{t('grievances.admin', 'Admin')}</span>;
      default: return <span className="px-1.5 py-0.5 bg-mitti-100 dark:bg-night-card text-mitti-600 dark:text-mitti-400 text-[10px] font-bold rounded uppercase ml-1.5">{t('grievances.you', 'You')}</span>;
    }
  };

  const getStageIndex = (status: string) => {
    if (status === 'rejected') return -1;
    const idx = LIFECYCLE_STAGES.indexOf(status as any);
    return idx >= 0 ? idx : 0;
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner size="lg" className="mx-auto" /></div>;
  if (grievances.length === 0) return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="village-card rounded-xl p-12 text-center">
      <AlertCircle className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('grievances.noGrievances', 'No grievances submitted yet.')}</p>
    </motion.div>
  );

  const visibleGrievances = grievances.slice(0, visibleCount);
  const hasMoreGrievances = grievances.length > visibleGrievances.length;

  return (
    <div className="space-y-4">
      {visibleGrievances.map((g: any, index: number) => {
        const currentStage = getStageIndex(g.status);
        const isRejected = g.status === 'rejected';

        return (
        <motion.div
          key={g.grievance_id}
          custom={index}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          className="village-card rounded-xl overflow-hidden"
        >
          <div className="p-5 cursor-pointer" onClick={() => toggleExpand(g.grievance_id)}>
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center flex-wrap gap-2 mb-1">
                  <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400 font-semibold">{g.grievance_id}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(g.status)}`}>{g.status?.toUpperCase()}</span>
                  {g.priority && <span className={`text-xs uppercase font-semibold ${g.priority === 'critical' ? 'text-red-500' : g.priority === 'high' ? 'text-orange-500' : 'text-mitti-500 dark:text-mitti-400'}`}>{g.priority}</span>}
                </div>
                <h3 className="font-semibold text-kora-100">{g.title || g.description?.slice(0, 80)}</h3>
                <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-1 flex flex-wrap gap-3">
                  {g.department && <span>{t('grievances.dept', 'Dept')}: {g.department}</span>}
                  {g.assigned_officer_name && <span><User className="w-3 h-3 inline mr-1" />{t('grievances.assignedOfficer', 'Officer')}: {g.assigned_officer_name}</span>}
                  {g.submitted_at && <span><Clock className="w-3 h-3 inline mr-1" />{new Date(g.submitted_at).toLocaleDateString()}</span>}
                </p>
              </div>
              <div className="flex items-center space-x-2 ml-4">
                {g.status === 'resolved' && !g.rating && (
                  <button onClick={(e) => { e.stopPropagation(); setRatingModal(g.grievance_id); }}
                    className="px-3 py-1 bg-mitti-100 dark:bg-mitti-800/20 text-mitti-600 dark:text-mitti-400 rounded-lg text-sm font-medium hover:bg-mitti-200 dark:hover:bg-mitti-800/30">
                    <Star className="w-4 h-4 inline mr-1" />{t('grievances.rate', 'Rate')}
                  </button>
                )}
                {g.status === 'resolved' && g.rating && (
                  <span className="px-3 py-1 bg-india-green-100 dark:bg-india-green-900/30 text-india-green-700 dark:text-india-green-400 rounded-lg text-sm font-medium">
                    <Star className="w-4 h-4 inline mr-1 fill-current" />{g.rating.rating}/5
                  </span>
                )}
                {expandedId === g.grievance_id ? <ChevronUp className="w-5 h-5 text-mitti-400" /> : <ChevronDown className="w-5 h-5 text-mitti-400" />}
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateRows: expandedId === g.grievance_id ? '1fr' : '0fr',
              transition: 'grid-template-rows 0.28s cubic-bezier(0.25, 1, 0.5, 1)',
            }}
          >
            <div className="overflow-hidden">
              <div style={{ opacity: expandedId === g.grievance_id ? 1 : 0, transition: 'opacity 0.2s ease' }}>
                <div className="border-t border-gray-200 dark:border-gray-700 p-5 space-y-5">

                  {/* ---- PROGRESS STEPPER ---- */}
                  {!isRejected && (
                    <div className="p-4 bg-mitti-50/50 dark:bg-mitti-800/20 rounded-xl">
                      <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-4">{t('grievances.grievanceProgress', 'Grievance Progress')}</h4>
                      <div className="flex items-center justify-between relative">
                        {/* Connecting line */}
                        <div className="absolute top-4 left-8 right-8 h-0.5 bg-gray-200 dark:bg-gray-600" />
                        <div className="absolute top-4 left-8 h-0.5 bg-india-green-500 dark:bg-india-green-400 transition-all duration-500"
                          style={{ width: currentStage <= 0 ? '0%' : `${(currentStage / (LIFECYCLE_STAGES.length - 1)) * 100}%`, maxWidth: 'calc(100% - 4rem)' }} />

                        {LIFECYCLE_STAGES.map((stage, idx) => {
                          const isComplete = idx <= currentStage;
                          const isCurrent = idx === currentStage;
                          return (
                            <div key={stage} className="flex flex-col items-center relative z-10">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all
                                ${isComplete
                                  ? 'bg-mitti-500 border-mitti-500 text-white'
                                  : 'bg-white dark:bg-night-surface border-gray-300 dark:border-gray-500 text-mitti-400 dark:text-night-muted'}
                                ${isCurrent ? 'ring-4 ring-saffron-200 dark:ring-saffron-900/50' : ''}`}>
                                {isComplete ? <Check className="w-4 h-4" /> : idx + 1}
                              </div>
                              <span className={`text-xs mt-2 font-medium ${isComplete ? 'text-mitti-600 dark:text-mitti-400' : 'text-mitti-400 dark:text-night-muted'}`}>
                                {STAGE_LABELS[stage]}
                              </span>
                              {stage === 'pending' && g.submitted_at && (
                                <span className="text-[10px] text-mitti-400 dark:text-night-muted mt-0.5">{new Date(g.submitted_at).toLocaleDateString()}</span>
                              )}
                              {stage === 'accepted' && g.accepted_at && (
                                <span className="text-[10px] text-mitti-400 dark:text-night-muted mt-0.5">{new Date(g.accepted_at).toLocaleDateString()}</span>
                              )}
                              {stage === 'resolved' && g.resolved_at && (
                                <span className="text-[10px] text-mitti-400 dark:text-night-muted mt-0.5">{new Date(g.resolved_at).toLocaleDateString()}</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Rejected banner */}
                  {isRejected && (
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                      <div className="flex items-center mb-2">
                        <X className="w-5 h-5 text-red-600 dark:text-red-400 mr-2" />
                        <span className="font-bold text-red-700 dark:text-red-400">{t('grievances.rejected', 'Grievance Rejected')}</span>
                      </div>
                      {g.resolution_notes && <p className="text-sm text-red-600 dark:text-red-300">{t('grievances.reason', 'Reason')}: {g.resolution_notes}</p>}
                    </div>
                  )}

                  {/* Description */}
                  <div>
                    <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-2">{t('grievances.descriptionLabel', 'Description')}</h4>
                    <p className="text-kora-300/70">{g.description}</p>
                  </div>

                  {/* Officer & Resolution Info */}
                  {(g.assigned_officer_name || g.resolution_notes) && !isRejected && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {g.assigned_officer_name && (
                        <div className="p-3 bg-mitti-50 dark:bg-mitti-800/20 border border-mitti-200 dark:border-mitti-700 rounded-lg">
                          <p className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase mb-1">{t('grievances.assignedOfficer', 'Assigned Officer')}</p>
                          <p className="text-sm font-medium text-kora-300/70 flex items-center">
                            <User className="w-4 h-4 mr-1.5" />{g.assigned_officer_name}
                          </p>
                        </div>
                      )}
                      {g.resolution_notes && g.status === 'resolved' && (
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                          <p className="text-xs font-bold text-green-600 dark:text-green-400 uppercase mb-1">{t('grievances.resolutionNotes', 'Resolution Notes')}</p>
                          <p className="text-sm text-green-800 dark:text-green-200">{g.resolution_notes}</p>
                          {g.resolved_at && <p className="text-[10px] text-green-500 dark:text-green-500 mt-1">{t('grievances.resolvedOn', 'Resolved on')} {new Date(g.resolved_at).toLocaleString()}</p>}
                        </div>
                      )}
                    </div>
                  )}

                  {/* AI Routing */}
                  {g.routing_reasoning && (
                    <div className="p-3 bg-mitti-50 dark:bg-mitti-800/20 rounded-lg border border-mitti-200 dark:border-mitti-700">
                      <p className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase mb-1">{t('grievances.aiReasoning', 'AI Routing Analysis')}</p>
                      <p className="text-sm text-kora-300/70">{g.routing_reasoning}</p>
                    </div>
                  )}

                  {/* Timeline History */}
                  {(timelines[g.grievance_id] || []).length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-3">{t('grievances.statusHistory', 'Status History')}</h4>
                      <div className="relative pl-6 space-y-3">
                        <div className="absolute left-2 top-1 bottom-1 w-0.5 bg-gray-200 dark:bg-gray-600" />
                        {(timelines[g.grievance_id] || []).map((tl: any, i: number) => (
                          <div key={i} className="relative">
                            <div className={`absolute -left-4 top-1.5 w-3 h-3 rounded-full border-2 ${
                              tl.new_status === 'resolved' ? 'bg-india-green-500 border-india-green-500' :
                              tl.new_status === 'rejected' ? 'bg-red-500 border-red-500' :
                              'bg-mitti-500 border-mitti-500'
                            }`} />
                            <div className="ml-2">
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-semibold text-kora-100 capitalize">{tl.new_status?.replace('_', ' ')}</span>
                                {tl.updated_by && <span className="text-xs text-mitti-500 dark:text-mitti-400">by {tl.updated_by}</span>}
                              </div>
                              {tl.notes && <p className="text-xs text-mitti-600 dark:text-mitti-400 mt-0.5">{tl.notes}</p>}
                              {tl.timestamp && <p className="text-[10px] text-mitti-400 dark:text-night-muted mt-0.5">{new Date(tl.timestamp).toLocaleString()}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Comments with role badges */}
                  <div>
                    <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-3 flex items-center">
                      <MessageSquare className="w-4 h-4 mr-2" />{t('grievances.messages', 'Messages')} ({(comments[g.grievance_id] || []).length})
                    </h4>
                    <div className="space-y-2 mb-3 max-h-64 overflow-y-auto" data-lenis-prevent>
                      {(comments[g.grievance_id] || []).map((c: any) => (
                        <div key={c.id} className={`p-3 rounded-lg ${
                          c.author_role === 'officer' ? 'bg-mitti-50 dark:bg-mitti-800/20 border border-mitti-100 dark:border-mitti-700' :
                          c.author_role === 'admin' ? 'bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800' :
                          'bg-gray-50 dark:bg-night-card/50'
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-kora-300/70 flex items-center">
                              <User className="w-3 h-3 mr-1" />{c.author_name || 'User'}
                              {getRoleBadge(c.author_role)}
                            </span>
                            <span className="text-xs text-mitti-500">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                          </div>
                          <p className="text-sm text-mitti-800 dark:text-kora-200">{c.comment_text}</p>
                        </div>
                      ))}
                      {(comments[g.grievance_id] || []).length === 0 && <p className="text-sm text-mitti-500 dark:text-mitti-400 italic">{t('grievances.noMessages', 'No messages yet.')}</p>}
                    </div>
                    {g.status !== 'resolved' && g.status !== 'rejected' && (
                      <div className="flex space-x-2">
                        <input type="text" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                          placeholder={t('grievances.sendMessagePlaceholder', 'Send a message...')} onKeyDown={(e) => e.key === 'Enter' && handleAddComment(g.grievance_id)}
                          className="village-input flex-1 px-3 py-2 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30" />
                        <button onClick={() => handleAddComment(g.grievance_id)}
                          className="px-4 py-2 bg-[#0D92F4] text-white rounded-lg hover:bg-mitti-600 text-sm font-medium flex items-center">
                          <Send className="w-4 h-4 mr-1" />{t('common.send', 'Send')}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
        );
      })}

      {hasMoreGrievances && (
        <div className="flex justify-center mt-2">
          <button
            type="button"
            onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
            className="px-5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm font-medium text-kora-100 hover:bg-white/[0.06] transition-colors"
          >
            Show more <span className="text-slate-500 ml-1">({grievances.length - visibleGrievances.length} remaining)</span>
          </button>
        </div>
      )}

      {/* Rating Modal */}
      <AnimatePresence>
        {ratingModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="village-card rounded-xl shadow-2xl w-full max-w-sm overflow-hidden"
            >
              <div className="bg-gradient-to-r from-mitti-500 to-haldi-500 p-5 text-white">
                <h3 className="text-lg font-bold flex items-center"><Star className="w-5 h-5 mr-2 fill-white" />{t('grievances.rateResolution', 'Rate Resolution')}</h3>
                <p className="text-sm text-mitti-200 mt-1">{t('grievances.howWasHandled', 'How was your grievance handled?')}</p>
              </div>
              <div className="p-6">
                <div className="flex justify-center space-x-2 mb-4">
                  {[1, 2, 3, 4, 5].map(s => (
                    <button key={s} onClick={() => setRating(s)} className="transition-transform hover:scale-110">
                      <Star className={`w-10 h-10 ${s <= rating ? 'text-mitti-500 fill-saffron-500' : 'text-mitti-300 dark:text-mitti-600'}`} />
                    </button>
                  ))}
                </div>
                <p className="text-center text-sm text-mitti-500 dark:text-mitti-400 mb-4">
                  {rating === 1 ? t('grievances.ratingPoor', 'Poor') : rating === 2 ? t('grievances.ratingBelowAvg', 'Below Average') : rating === 3 ? t('grievances.ratingAverage', 'Average') : rating === 4 ? t('grievances.ratingGood', 'Good') : t('grievances.ratingExcellent', 'Excellent')}
                </p>
                <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} rows={3} placeholder={t('grievances.feedbackPlaceholder', 'Share your feedback (optional)...')}
                  className="village-input w-full px-3 py-2 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30 mb-4" />
                <div className="flex justify-end space-x-3">
                  <button onClick={() => setRatingModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-kora-300/70 hover:bg-gray-50 dark:hover:bg-night-card/50">{t('common.cancel', 'Cancel')}</button>
                  <button onClick={() => handleRate(ratingModal)} className="btn-mitti px-4 py-2 rounded-lg text-white font-medium">{t('grievances.submitRating', 'Submit Rating')}</button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* ===================== DEPARTMENT INBOX (OFFICER) ===================== */
const DepartmentInboxTab: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const officerName = user?.username || '';
  const [grievances, setGrievances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionModal, setActionModal] = useState<{ type: string; id: string } | null>(null);
  const [formData, setFormData] = useState({ notes: '', reason: '' });
  const [actionLoading, setActionLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, any[]>>({});
  const [newComment, setNewComment] = useState('');

  useEffect(() => { loadInbox(); }, []);

  const loadInbox = async () => {
    setLoading(true);
    try {
      const data = await apiService.getDepartmentInbox();
      setGrievances(data.grievances || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const loadComments = async (grievanceId: string) => {
    try {
      const data = await apiService.getGrievanceComments(grievanceId);
      setComments(prev => ({ ...prev, [grievanceId]: data.comments || [] }));
    } catch { /* ignore */ }
  };

  const handleAddComment = async (grievanceId: string) => {
    if (!newComment.trim()) return;
    try {
      await apiService.addGrievanceComment(grievanceId, newComment, 'note', true);
      setNewComment('');
      loadComments(grievanceId);
    } catch { /* ignore */ }
  };

  const handleAccept = async () => {
    if (!actionModal) return;
    setActionLoading(true);
    try {
      await apiService.acceptGrievance(actionModal.id, officerName, formData.notes || undefined);
      setActionModal(null);
      setFormData({ notes: '', reason: '' });
      loadInbox();
    } catch { toast.error('Failed to accept'); } finally { setActionLoading(false); }
  };

  const handleReject = async () => {
    if (!actionModal || !formData.reason) return;
    setActionLoading(true);
    try {
      await apiService.rejectGrievance(actionModal.id, officerName, formData.reason);
      setActionModal(null);
      setFormData({ notes: '', reason: '' });
      loadInbox();
    } catch { toast.error('Failed to reject'); } finally { setActionLoading(false); }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400';
      case 'accepted': return 'bg-mitti-100 text-mitti-600 dark:bg-mitti-800/20 dark:text-mitti-400';
      case 'in_progress': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      default: return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
    }
  };

  const getPriorityColor = (p: string) => {
    switch (p?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'high': return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
      case 'medium': return 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400';
      default: return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    }
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner size="lg" className="mx-auto" /></div>;
  if (grievances.length === 0) return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="village-card rounded-xl p-12 text-center">
      <Inbox className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('grievances.noPendingInbox', 'No pending grievances in your department.')}</p>
    </motion.div>
  );

  return (
    <>
      <div className="space-y-4">
        {grievances.map((g: any, index: number) => (
          <motion.div
            key={g.grievance_id}
            custom={index}
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className="village-card rounded-xl overflow-hidden"
          >
            <div className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center flex-wrap gap-2 mb-2">
                    <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400 font-semibold">{g.grievance_id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(g.status)}`}>{g.status?.toUpperCase()}</span>
                    {g.priority && <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getPriorityColor(g.priority)}`}>{g.priority?.toUpperCase()}</span>}
                    <span className="text-xs text-mitti-500 dark:text-mitti-400"><Clock className="w-3 h-3 inline mr-1" />{g.submitted_at ? new Date(g.submitted_at).toLocaleDateString() : ''}</span>
                  </div>
                  <h3 className="font-semibold text-kora-100 mb-1">{g.title || g.description?.slice(0, 100)}</h3>
                  <p className="text-sm text-mitti-600 dark:text-mitti-300 mb-2">{g.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs text-mitti-500 dark:text-mitti-400">
                    {g.citizen_name && <span><User className="w-3 h-3 inline mr-1" />{g.citizen_name}</span>}
                    {g.category && <span className="capitalize">{g.category?.replace('_', ' ')}</span>}
                  </div>
                </div>
                {g.status === 'pending' && (
                  <div className="flex flex-col space-y-2 ml-4">
                    <button onClick={() => setActionModal({ type: 'accept', id: g.grievance_id })}
                      className="px-4 py-2 bg-india-green-600 text-white rounded-lg text-sm font-semibold hover:bg-india-green-700 flex items-center">
                      <Check className="w-4 h-4 mr-1" />{t('grievances.accept', 'Accept')}
                    </button>
                    <button onClick={() => setActionModal({ type: 'reject', id: g.grievance_id })}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 flex items-center">
                      <X className="w-4 h-4 mr-1" />{t('grievances.reject', 'Reject')}
                    </button>
                  </div>
                )}
              </div>

              {/* Expandable details + comments */}
              <button onClick={() => { if (expandedId === g.grievance_id) { setExpandedId(null); } else { setExpandedId(g.grievance_id); if (!comments[g.grievance_id]) loadComments(g.grievance_id); } }}
                className="mt-3 text-sm text-mitti-500 dark:text-mitti-400 hover:underline flex items-center">
                <MessageSquare className="w-4 h-4 mr-1" />
                {expandedId === g.grievance_id ? t('grievances.hideComments', 'Hide Comments') : t('grievances.showComments', 'Show Comments')}
              </button>

              <div
                style={{
                  display: 'grid',
                  gridTemplateRows: expandedId === g.grievance_id ? '1fr' : '0fr',
                  transition: 'grid-template-rows 0.28s cubic-bezier(0.25, 1, 0.5, 1)',
                }}
              >
                <div className="overflow-hidden">
                  <div style={{ opacity: expandedId === g.grievance_id ? 1 : 0, transition: 'opacity 0.2s ease' }}>
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
                      {(comments[g.grievance_id] || []).map((c: any) => (
                        <div key={c.id} className="p-2 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-kora-300/70">{c.author_name || 'User'} {c.author_role ? `(${c.author_role})` : ''}</span>
                            <span className="text-xs text-mitti-500">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                          </div>
                          <p className="text-sm text-mitti-800 dark:text-kora-200">{c.comment_text}</p>
                        </div>
                      ))}
                      {(comments[g.grievance_id] || []).length === 0 && <p className="text-xs text-mitti-500">{t('grievances.noComments', 'No comments yet.')}</p>}
                      <div className="flex space-x-2 mt-2">
                        <input type="text" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                          placeholder={t('grievances.addComment', 'Add a comment...')} onKeyDown={(e) => e.key === 'Enter' && handleAddComment(g.grievance_id)}
                          className="village-input flex-1 px-3 py-1.5 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30" />
                        <button onClick={() => handleAddComment(g.grievance_id)}
                          className="px-3 py-1.5 bg-[#0D92F4] text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.send', 'Send')}</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <AnimatePresence>
        {actionModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="village-card rounded-xl shadow-2xl w-full max-w-md p-6"
            >
              <h3 className="text-lg font-bold text-kora-100 mb-4">
                {actionModal.type === 'accept' ? t('grievances.acceptGrievance', 'Accept Grievance') : t('grievances.rejectGrievance', 'Reject Grievance')}
              </h3>
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                  <p className="text-xs text-mitti-500 dark:text-mitti-400 mb-1">{t('grievances.actingAs', 'Acting as')}</p>
                  <p className="font-semibold text-kora-100">{officerName}</p>
                </div>
                {actionModal.type === 'accept' && (
                  <div>
                    <label className="block text-sm font-medium text-kora-300/70 mb-1">{t('grievances.notesOptional', 'Notes (optional)')}</label>
                    <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30" rows={3} placeholder={t('grievances.addNotesPlaceholder', 'Add notes...')} />
                  </div>
                )}
                {actionModal.type === 'reject' && (
                  <div>
                    <label className="block text-sm font-medium text-kora-300/70 mb-1">{t('grievances.rejectionReason', 'Rejection Reason')} *</label>
                    <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                      className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30" rows={3} placeholder={t('grievances.rejectionReasonPlaceholder', 'Reason for rejection...')} />
                  </div>
                )}
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button onClick={() => { setActionModal(null); setFormData({ notes: '', reason: '' }); }}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-kora-300/70">{t('common.cancel', 'Cancel')}</button>
                <button onClick={actionModal.type === 'accept' ? handleAccept : handleReject}
                  disabled={actionLoading || (actionModal.type === 'reject' && !formData.reason)}
                  className={`px-4 py-2 rounded-lg text-white font-medium disabled:bg-gray-400 ${
                    actionModal.type === 'accept' ? 'bg-india-green-600 hover:bg-india-green-700' : 'bg-red-600 hover:bg-red-700'
                  }`}>
                  {actionLoading ? t('grievances.processing', 'Processing...') : actionModal.type === 'accept' ? t('grievances.accept', 'Accept') : t('grievances.reject', 'Reject')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

/* ===================== MY CASES (OFFICER - ASSIGNED TO ME) ===================== */
const MyCasesTab: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const officerName = user?.username || '';
  const [grievances, setGrievances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionModal, setActionModal] = useState<{ type: string; id: string } | null>(null);
  const [formData, setFormData] = useState({ notes: '' });
  const [actionLoading, setActionLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, any[]>>({});
  const [newComment, setNewComment] = useState('');

  useEffect(() => { loadAssigned(); }, []);

  const loadAssigned = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAssignedGrievances();
      setGrievances(data.grievances || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const loadComments = async (grievanceId: string) => {
    try {
      const data = await apiService.getGrievanceComments(grievanceId);
      setComments(prev => ({ ...prev, [grievanceId]: data.comments || [] }));
    } catch { /* ignore */ }
  };

  const handleAddComment = async (grievanceId: string) => {
    if (!newComment.trim()) return;
    try {
      await apiService.addGrievanceComment(grievanceId, newComment, 'note', true);
      setNewComment('');
      loadComments(grievanceId);
    } catch { /* ignore */ }
  };

  const handleAction = async () => {
    if (!actionModal) return;
    setActionLoading(true);
    try {
      if (actionModal.type === 'resolve') {
        await apiService.resolveGrievance(actionModal.id, officerName, formData.notes);
      } else if (actionModal.type === 'update') {
        await apiService.updateGrievanceStatus(actionModal.id, 'in_progress', officerName, formData.notes);
      }
      setActionModal(null);
      setFormData({ notes: '' });
      loadAssigned();
    } catch { toast.error('Action failed'); } finally { setActionLoading(false); }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      case 'accepted': return 'bg-mitti-100 text-mitti-600 dark:bg-mitti-800/20 dark:text-mitti-400';
      case 'in_progress': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      default: return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
    }
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner size="lg" className="mx-auto" /></div>;
  if (grievances.length === 0) return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="village-card rounded-xl p-12 text-center">
      <Briefcase className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('grievances.noCasesAssigned', 'No cases assigned to you yet. Accept grievances from the Department Inbox.')}</p>
    </motion.div>
  );

  return (
    <>
      <div className="space-y-4">
        {grievances.map((g: any, index: number) => (
          <motion.div
            key={g.grievance_id}
            custom={index}
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className="village-card rounded-xl p-5"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center flex-wrap gap-2 mb-1">
                  <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400 font-semibold">{g.grievance_id}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(g.status)}`}>{g.status?.toUpperCase()}</span>
                  {g.priority && <span className="text-xs text-mitti-500 uppercase">{g.priority}</span>}
                </div>
                <h3 className="font-semibold text-kora-100 mb-1">{g.title || g.description?.slice(0, 80)}</h3>
                <p className="text-sm text-mitti-600 dark:text-mitti-300 mb-2">{g.description}</p>
                <div className="flex flex-wrap gap-3 text-xs text-mitti-500 dark:text-mitti-400">
                  {g.citizen_name && <span><User className="w-3 h-3 inline mr-1" />{g.citizen_name}</span>}
                  {g.submitted_at && <span><Clock className="w-3 h-3 inline mr-1" />{new Date(g.submitted_at).toLocaleDateString()}</span>}
                </div>
              </div>
              <div className="flex space-x-2 ml-4">
                {g.status !== 'resolved' && (
                  <>
                    {g.status === 'accepted' && (
                      <button onClick={() => setActionModal({ type: 'update', id: g.grievance_id })}
                        className="px-3 py-2 bg-[#0D92F4] text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.inProgress', 'In Progress')}</button>
                    )}
                    <button onClick={() => setActionModal({ type: 'resolve', id: g.grievance_id })}
                      className="px-3 py-2 bg-india-green-600 text-white rounded-lg text-sm font-medium hover:bg-india-green-700">{t('grievances.resolve', 'Resolve')}</button>
                  </>
                )}
              </div>
            </div>

            {/* Comments */}
            <button onClick={() => { if (expandedId === g.grievance_id) { setExpandedId(null); } else { setExpandedId(g.grievance_id); if (!comments[g.grievance_id]) loadComments(g.grievance_id); } }}
              className="mt-3 text-sm text-mitti-500 dark:text-mitti-400 hover:underline flex items-center">
              <MessageSquare className="w-4 h-4 mr-1" />
              {expandedId === g.grievance_id ? t('grievances.hideComments', 'Hide Comments') : t('grievances.comments', 'Comments')}
            </button>

            <div
              style={{
                display: 'grid',
                gridTemplateRows: expandedId === g.grievance_id ? '1fr' : '0fr',
                transition: 'grid-template-rows 0.28s cubic-bezier(0.25, 1, 0.5, 1)',
              }}
            >
              <div className="overflow-hidden">
                <div style={{ opacity: expandedId === g.grievance_id ? 1 : 0, transition: 'opacity 0.2s ease' }}>
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
                    {(comments[g.grievance_id] || []).map((c: any) => (
                      <div key={c.id} className="p-2 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-kora-300/70">{c.author_name || 'User'}</span>
                          <span className="text-xs text-mitti-500">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                        </div>
                        <p className="text-sm text-mitti-800 dark:text-kora-200">{c.comment_text}</p>
                      </div>
                    ))}
                    {(comments[g.grievance_id] || []).length === 0 && <p className="text-xs text-mitti-500">{t('grievances.noComments', 'No comments yet.')}</p>}
                    <div className="flex space-x-2 mt-2">
                      <input type="text" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                        placeholder={t('grievances.addComment', 'Add comment...')} onKeyDown={(e) => e.key === 'Enter' && handleAddComment(g.grievance_id)}
                        className="village-input flex-1 px-3 py-1.5 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30" />
                      <button onClick={() => handleAddComment(g.grievance_id)}
                        className="px-3 py-1.5 bg-[#0D92F4] text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.send', 'Send')}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <AnimatePresence>
        {actionModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="village-card rounded-xl shadow-2xl w-full max-w-md p-6"
            >
              <h3 className="text-lg font-bold text-kora-100 mb-4">
                {actionModal.type === 'resolve' ? t('grievances.resolveGrievance', 'Resolve Grievance') : t('grievances.updateToInProgress', 'Update to In Progress')}
              </h3>
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                  <p className="text-xs text-mitti-500 mb-1">{t('grievances.actingAs', 'Acting as')}</p>
                  <p className="font-semibold text-kora-100">{officerName}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-kora-300/70 mb-1">
                    {actionModal.type === 'resolve' ? t('grievances.resolutionNotesRequired', 'Resolution Notes *') : t('grievances.notes', 'Notes')}
                  </label>
                  <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} rows={3}
                    className="village-input w-full px-3 py-2 rounded-lg text-kora-100 focus:ring-2 focus:ring-[#0D92F4]/30"
                    placeholder={actionModal.type === 'resolve' ? t('grievances.resolvePlaceholder', 'How was this resolved...') : t('grievances.addNotesPlaceholder', 'Add notes...')} />
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button onClick={() => setActionModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-kora-300/70">{t('common.cancel', 'Cancel')}</button>
                <button onClick={handleAction} disabled={actionLoading || (actionModal.type === 'resolve' && !formData.notes)}
                  className="btn-mitti px-4 py-2 rounded-lg text-white font-medium disabled:bg-gray-400">
                  {actionLoading ? t('grievances.processing', 'Processing...') : t('common.submit', 'Submit')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

/* ===================== ALL GRIEVANCES (ADMIN) ===================== */
const AllGrievancesTab: React.FC = () => {
  const { t } = useTranslation();
  const [grievances, setGrievances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => { loadAll(); }, [statusFilter, deptFilter]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAllGrievances(statusFilter || undefined, deptFilter || undefined);
      setGrievances(data.grievances || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const handleCardClick = async (grievanceId: string) => {
    if (expandedId === grievanceId) {
      setExpandedId(null);
      setDetailData(null);
      return;
    }
    setExpandedId(grievanceId);
    setDetailLoading(true);
    try {
      const data = await apiService.getGrievanceDetail(grievanceId);
      setDetailData(data);
    } catch {
      toast.error('Failed to load grievance details');
      setDetailData(null);
    } finally { setDetailLoading(false); }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      case 'pending': return 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400';
      case 'accepted': return 'bg-mitti-100 text-mitti-600 dark:bg-mitti-800/20 dark:text-mitti-400';
      case 'in_progress': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      case 'rejected': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default: return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap gap-3">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="village-input px-3 py-2 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30">
          <option value="">{t('grievances.allStatuses', 'All Statuses')}</option>
          <option value="pending">{t('common.pending', 'Pending')}</option>
          <option value="accepted">{t('common.accepted', 'Accepted')}</option>
          <option value="in_progress">{t('common.inProgress', 'In Progress')}</option>
          <option value="resolved">{t('common.resolved', 'Resolved')}</option>
          <option value="rejected">{t('common.rejected', 'Rejected')}</option>
        </select>
        <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}
          className="village-input px-3 py-2 rounded-lg text-kora-100 text-sm focus:ring-2 focus:ring-[#0D92F4]/30">
          <option value="">{t('grievances.allDepartments', 'All Departments')}</option>
          {['Agriculture', 'Rural Development', 'Social Welfare', 'Urban Development', 'Labor & Employment', 'Finance', 'Housing', 'Education', 'Health', 'General Administration'].map(d =>
            <option key={d} value={d}>{d}</option>
          )}
        </select>
        <span className="px-3 py-2 text-sm text-mitti-500 dark:text-mitti-400">{grievances.length} {t('grievances.grievancesCount', 'grievances')}</span>
      </motion.div>

      {loading ? (
        <div className="text-center py-12"><ThemedSpinner size="lg" className="mx-auto" /></div>
      ) : grievances.length === 0 ? (
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="village-card rounded-xl p-12 text-center">
          <AlertCircle className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
          <p className="text-mitti-600 dark:text-mitti-400">{t('grievances.noGrievancesFound', 'No grievances found.')}</p>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {grievances.map((g: any, index: number) => (
            <motion.div
              key={g.grievance_id}
              custom={index}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className={`village-card rounded-xl p-4 cursor-pointer transition-all ${expandedId === g.grievance_id ? 'ring-2 ring-mitti-500/40' : 'hover:shadow-elevated'}`}
              onClick={() => handleCardClick(g.grievance_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-wrap gap-2 mb-2">
                  <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400 font-semibold">{g.grievance_id}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(g.status)}`}>{g.status?.toUpperCase()}</span>
                  {g.priority && <span className="text-xs text-mitti-500 uppercase font-bold">{g.priority}</span>}
                  {g.department && <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-full">{g.department}</span>}
                  <span className="text-xs text-mitti-500"><Clock className="w-3 h-3 inline mr-1" />{g.submitted_at ? new Date(g.submitted_at).toLocaleDateString() : ''}</span>
                </div>
                {expandedId === g.grievance_id ? <ChevronUp className="w-5 h-5 text-mitti-400 flex-shrink-0" /> : <ChevronDown className="w-5 h-5 text-mitti-400 flex-shrink-0" />}
              </div>
              <h3 className="font-semibold text-kora-100 mb-1">{g.title || g.description?.slice(0, 100)}</h3>
              <p className="text-sm text-mitti-600 dark:text-mitti-300 line-clamp-2">{g.description}</p>
              <div className="flex flex-wrap gap-3 text-xs text-mitti-500 dark:text-mitti-400 mt-2">
                {g.citizen_name && <span><User className="w-3 h-3 inline mr-1" />{g.citizen_name}</span>}
                {g.assigned_officer_name && <span>{t('grievances.assigned', 'Assigned')}: {g.assigned_officer_name}</span>}
              </div>

              {/* Expanded Detail View */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateRows: expandedId === g.grievance_id ? '1fr' : '0fr',
                  transition: 'grid-template-rows 0.28s cubic-bezier(0.25, 1, 0.5, 1)',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="overflow-hidden">
                  <div style={{ opacity: expandedId === g.grievance_id ? 1 : 0, transition: 'opacity 0.2s ease' }}>
                    <div className="mt-4 pt-4 border-t border-mitti-200/30 dark:border-night-border/40">
                      {detailLoading ? (
                        <div className="flex items-center justify-center py-6">
                          <ThemedSpinner size="sm" />
                          <span className="ml-2 text-sm text-mitti-500">Loading details...</span>
                        </div>
                      ) : detailData ? (
                        <div className="space-y-4">
                          {/* Full Description */}
                          <div>
                            <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-1">Full Description</h4>
                            <p className="text-sm text-kora-300/70 leading-relaxed">{detailData.description}</p>
                          </div>

                          {/* Info Grid */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {detailData.citizen_name && (
                              <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-2.5">
                                <p className="text-xs text-mitti-400 dark:text-mitti-500">Citizen</p>
                                <p className="text-sm font-medium text-mitti-800 dark:text-kora-200">{detailData.citizen_name}</p>
                              </div>
                            )}
                            {detailData.citizen_email && (
                              <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-2.5">
                                <p className="text-xs text-mitti-400 dark:text-mitti-500">Email</p>
                                <p className="text-sm font-medium text-mitti-800 dark:text-kora-200 truncate">{detailData.citizen_email}</p>
                              </div>
                            )}
                            {detailData.department && (
                              <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-2.5">
                                <p className="text-xs text-mitti-400 dark:text-mitti-500">Department</p>
                                <p className="text-sm font-medium text-mitti-800 dark:text-kora-200">{detailData.department}</p>
                              </div>
                            )}
                            {detailData.assigned_officer_name && (
                              <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-2.5">
                                <p className="text-xs text-mitti-400 dark:text-mitti-500">Assigned To</p>
                                <p className="text-sm font-medium text-mitti-800 dark:text-kora-200">{detailData.assigned_officer_name}</p>
                              </div>
                            )}
                          </div>

                          {/* SLA Info */}
                          {detailData.sla && (
                            <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-3">
                              <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-2">SLA Status</h4>
                              <div className="flex flex-wrap gap-3 text-sm">
                                <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${detailData.sla.breached ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400'}`}>
                                  {detailData.sla.breached ? 'SLA Breached' : 'Within SLA'}
                                </span>
                                {detailData.sla.hours_remaining != null && (
                                  <span className="text-mitti-600 dark:text-mitti-300">{Math.round(detailData.sla.hours_remaining)}h remaining</span>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Timeline */}
                          {detailData.timeline && detailData.timeline.length > 0 && (
                            <div>
                              <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-2">Timeline</h4>
                              <div className="space-y-2 max-h-48 overflow-y-auto" data-lenis-prevent>
                                {detailData.timeline.map((entry: any, i: number) => (
                                  <div key={i} className="flex items-start gap-3 text-sm">
                                    <div className="w-2 h-2 mt-1.5 rounded-full bg-mitti-400 flex-shrink-0" />
                                    <div>
                                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold mr-2 ${getStatusColor(entry.new_status)}`}>{entry.new_status}</span>
                                      {entry.update_notes && <span className="text-mitti-600 dark:text-mitti-300">{entry.update_notes}</span>}
                                      <p className="text-xs text-mitti-400 mt-0.5">{new Date(entry.timestamp).toLocaleString()}</p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Comments */}
                          {detailData.comments && detailData.comments.length > 0 && (
                            <div>
                              <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-2 flex items-center">
                                <MessageSquare className="w-3.5 h-3.5 mr-1.5" />Comments ({detailData.comments.length})
                              </h4>
                              <div className="space-y-2 max-h-48 overflow-y-auto" data-lenis-prevent>
                                {detailData.comments.map((c: any) => (
                                  <div key={c.id} className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-xs font-bold text-mitti-700 dark:text-kora-200">{c.author_name}</span>
                                      <span className="text-xs px-1.5 py-0.5 rounded bg-mitti-100/50 dark:bg-night-card/50 text-mitti-500 capitalize">{c.author_role}</span>
                                      <span className="text-xs text-mitti-400">{new Date(c.created_at).toLocaleString()}</span>
                                    </div>
                                    <p className="text-sm text-mitti-600 dark:text-mitti-300">{c.comment_text}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Rating */}
                          {detailData.rating && (
                            <div className="bg-kora-50/60 dark:bg-night-card/40 rounded-lg p-3">
                              <h4 className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase tracking-wider mb-1">Citizen Rating</h4>
                              <div className="flex items-center gap-1">
                                {[1, 2, 3, 4, 5].map((s) => (
                                  <Star key={s} className={`w-4 h-4 ${s <= detailData.rating.rating ? 'text-haldi-500 fill-haldi-500' : 'text-mitti-300'}`} />
                                ))}
                                {detailData.rating.feedback_text && <span className="ml-2 text-sm text-mitti-600 dark:text-mitti-300">{detailData.rating.feedback_text}</span>}
                              </div>
                            </div>
                          )}

                          {/* Resolution Notes */}
                          {detailData.resolution_notes && (
                            <div className="bg-india-green-50/60 dark:bg-india-green-900/10 border border-india-green-200/40 dark:border-india-green-700/20 rounded-lg p-3">
                              <h4 className="text-xs font-bold text-india-green-700 dark:text-india-green-400 uppercase tracking-wider mb-1">Resolution</h4>
                              <p className="text-sm text-india-green-800 dark:text-india-green-300">{detailData.resolution_notes}</p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-sm text-mitti-500 py-4 text-center">Could not load details.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

/* ===================== ANALYTICS TAB (ADMIN) ===================== */
const AnalyticsTab: React.FC = () => {
  const { t } = useTranslation();
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiService.getGrievanceAnalytics()
      .then(setAnalytics)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12"><ThemedSpinner size="lg" className="mx-auto" /></div>;
  if (!analytics) return <p className="text-mitti-500 text-center py-8">{t('grievances.noAnalytics', 'No analytics data available.')}</p>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible" className="village-card rounded-xl p-5">
          <p className="text-sm text-mitti-500 dark:text-mitti-400">{t('grievances.totalGrievances', 'Total Grievances')}</p>
          <p className="text-3xl font-bold text-kora-100">{analytics.total || 0}</p>
        </motion.div>
        <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible" className="village-card rounded-xl p-5">
          <p className="text-sm text-mitti-500 dark:text-mitti-400">{t('grievances.resolutionRate', 'Resolution Rate')}</p>
          <p className="text-3xl font-bold text-india-green-600 dark:text-india-green-400">{analytics.resolution_rate || 0}%</p>
        </motion.div>
        <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible" className="village-card rounded-xl p-5">
          <p className="text-sm text-mitti-500 dark:text-mitti-400">{t('grievances.avgResolutionTime', 'Avg Resolution Time')}</p>
          <p className="text-3xl font-bold text-mitti-500 dark:text-mitti-400">{analytics.avg_resolution_hours ? `${Math.round(analytics.avg_resolution_hours)}h` : 'N/A'}</p>
        </motion.div>
      </div>

      {analytics.by_department && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="village-card rounded-xl p-6">
          <h3 className="text-lg font-semibold text-kora-100 mb-4">{t('grievances.byDepartment', 'By Department')}</h3>
          <div className="space-y-2">
            {Object.entries(analytics.by_department).map(([dept, count]: [string, any]) => (
              <div key={dept} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                <span className="font-medium text-kora-100 capitalize">{dept}</span>
                <span className="text-sm font-bold text-kora-300/70">{count}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {analytics.by_status && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="village-card rounded-xl p-6">
          <h3 className="text-lg font-semibold text-kora-100 mb-4">{t('grievances.byStatus', 'By Status')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(analytics.by_status).map(([status, count]: [string, any]) => (
              <div key={status} className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg text-center">
                <p className="text-xs text-mitti-500 dark:text-mitti-400 uppercase">{status}</p>
                <p className="text-xl font-bold text-kora-100">{count}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Grievances;
