import React, { useState, useEffect } from 'react';
import {
  FileText, Copy, CheckCircle, AlertCircle, Calendar, FileSignature,
  Building2, Send, Trash2, Clock, Search, Filter, X, Edit2, ShieldCheck,
  XCircle, Eye, Globe,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import toast from 'react-hot-toast';
import apiService from '../services/api';

/* ============================================================
   MAIN COMPONENT
   ============================================================ */
const NoticeDrafter: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const role = user?.role || 'citizen';

  const allTabs = [
    { id: 'generate', label: t('notices.generateTab', 'Generate'), roles: ['officer', 'admin'] },
    { id: 'drafts', label: t('notices.draftsTab', 'My Drafts'), roles: ['officer', 'admin'] },
    { id: 'review', label: t('notices.reviewTab', 'Review'), roles: ['admin'] },
    { id: 'published', label: t('notices.publishedTab', 'Published'), roles: ['officer', 'admin'] },
    { id: 'public', label: t('notices.publicBoardTab', 'Public Board'), roles: ['citizen', 'officer', 'admin'] },
  ];

  const visibleTabs = allTabs.filter((tab) => tab.roles.includes(role));
  const defaultTab = visibleTabs.length > 0 ? visibleTabs[0].id : 'public';
  const [activeTab, setActiveTab] = useState(defaultTab);

  useEffect(() => {
    const ids = visibleTabs.map((tab) => tab.id);
    if (!ids.includes(activeTab)) {
      setActiveTab(ids[0] || 'public');
    }
  }, [role]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <PageTransition>
      <div className="p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <h1 className="text-2xl md:text-3xl font-bold text-kora-100 tracking-tight mb-2">
              {t('notices.title', 'Official Notice Drafter')}
            </h1>
            <p className="text-sm text-mitti-500/40">
              {t('notices.subtitle', 'Generate, manage, and publish government notices')}
            </p>
          </motion.div>

          <div className="flex space-x-2 mb-6 village-card p-2 rounded-xl inline-flex flex-wrap gap-1">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2 rounded-lg font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-mitti-500 text-white shadow-lg'
                    : 'text-mitti-600 dark:text-mitti-400 hover:bg-white/10 dark:hover:bg-night-card/50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              {activeTab === 'generate' && <GenerateTab />}
              {activeTab === 'drafts' && <DraftsTab />}
              {activeTab === 'review' && <ReviewTab />}
              {activeTab === 'published' && <PublishedTab />}
              {activeTab === 'public' && <PublicBoardTab />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </PageTransition>
  );
};

/* ============================================================
   GENERATE TAB
   ============================================================ */
const GenerateTab: React.FC = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    scheme_name: '',
    notice_type: 'circular',
    language: 'en',
    effective_date: '',
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedNotice, setGeneratedNotice] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const noticeTypes = [
    { value: 'circular', label: t('notices.circular', 'Circular'), icon: FileText },
    { value: 'memo', label: t('notices.memorandum', 'Memorandum'), icon: FileSignature },
    { value: 'order', label: t('notices.governmentOrder', 'Government Order'), icon: Building2 },
    { value: 'notification', label: t('notices.notification', 'Notification'), icon: Calendar },
    { value: 'advisory', label: t('notices.advisory', 'Advisory'), icon: AlertCircle },
    { value: 'amendment', label: t('notices.amendment', 'Amendment'), icon: FileSignature },
  ];

  const handleGenerate = async () => {
    if (!formData.scheme_name.trim()) return;
    setIsGenerating(true);
    setError(null);
    setSaved(false);
    try {
      const response = await apiService.generateNotice({
        scheme_name: formData.scheme_name.trim(),
        notice_type: formData.notice_type,
        language: formData.language,
        effective_date: formData.effective_date || undefined,
      });
      setGeneratedNotice(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate notice.');
      setGeneratedNotice(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!generatedNotice?.formatted_notice) return;
    await navigator.clipboard.writeText(generatedNotice.formatted_notice);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveDraft = async () => {
    if (!generatedNotice) return;
    setSaving(true);
    try {
      await apiService.saveNoticeDraft({
        scheme_name: generatedNotice.scheme_name || formData.scheme_name,
        notice_type: generatedNotice.notice_type || formData.notice_type,
        subject: generatedNotice.subject || '',
        body: generatedNotice.body || '',
        formatted_notice: generatedNotice.formatted_notice || '',
        language: formData.language,
        effective_date: formData.effective_date || undefined,
      });
      setSaved(true);
    } catch {
      setError('Failed to save draft');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left column: form */}
      <div className="space-y-5">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
          className="village-card rounded-xl p-5"
        >
          <h2 className="font-semibold text-mitti-900 dark:text-kora-100 mb-3">
            {t('notices.noticeType', 'Notice Type')}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {noticeTypes.map((type) => {
              const Icon = type.icon;
              const sel = formData.notice_type === type.value;
              return (
                <button
                  key={type.value}
                  onClick={() => setFormData({ ...formData, notice_type: type.value })}
                  className={`p-3 rounded-lg border-2 transition-all text-left flex flex-col items-start space-y-1 ${
                    sel
                      ? 'border-mitti-500 bg-mitti-50 dark:bg-mitti-800/20'
                      : 'border-mitti-200/20 dark:border-gray-600 hover:border-mitti-300 dark:hover:border-mitti-500/50 bg-white/5'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${sel ? 'text-mitti-500' : 'text-mitti-500'}`} />
                  <span className={`font-medium text-xs ${sel ? 'text-mitti-600 dark:text-mitti-400' : 'text-mitti-700 dark:text-mitti-300'}`}>
                    {type.label}
                  </span>
                </button>
              );
            })}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="village-card rounded-xl p-5 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">
              {t('notices.subject', 'Scheme Name')} *
            </label>
            <input type="text" value={formData.scheme_name} onChange={(e) => setFormData({ ...formData, scheme_name: e.target.value })}
              placeholder="e.g., PM-KISAN, MGNREGA"
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">
              {t('notices.effectiveDate', 'Effective Date')}
            </label>
            <input type="date" value={formData.effective_date} onChange={(e) => setFormData({ ...formData, effective_date: e.target.value })}
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">Language</label>
            <div className="flex space-x-3">
              {[{ val: 'en', label: 'English' }, { val: 'hi', label: 'Hindi' }].map((l) => (
                <button key={l.val} onClick={() => setFormData({ ...formData, language: l.val })}
                  className={`flex-1 py-2 rounded-lg font-medium transition-all ${
                    formData.language === l.val ? 'bg-mitti-500 text-white shadow-md' : 'village-input text-mitti-600 dark:text-mitti-300'
                  }`}>{l.label}</button>
              ))}
            </div>
          </div>
        </motion.div>

        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGenerate}
          disabled={isGenerating || !formData.scheme_name.trim()}
          className="w-full py-3 btn-mitti bg-gradient-to-r from-mitti-500 to-haldi-500 text-white rounded-lg font-semibold hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {isGenerating ? (<><ThemedSpinner /><span>{t('notices.generate', 'Generating')}...</span></>) : (<><FileText className="w-5 h-5" /><span>{t('notices.generateNotice', 'Generate Notice')}</span></>)}
        </motion.button>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start space-x-2"
          >
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </motion.div>
        )}
      </div>

      {/* Right column: preview */}
      <div>
        {generatedNotice ? (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="village-card rounded-xl overflow-hidden"
          >
            <div className="bg-gradient-to-r from-mitti-500 to-haldi-500 px-5 py-3 text-white flex items-center justify-between">
              <h2 className="font-semibold flex items-center"><FileText className="w-5 h-5 mr-2" />{t('notices.formattedNotice', 'Generated Notice')}</h2>
              <button onClick={handleCopy} className="px-3 py-1 bg-white/20 rounded-lg text-sm hover:bg-mitti-100/50 flex items-center transition-all">
                {copied ? (<><CheckCircle className="w-4 h-4 mr-1" />{t('notices.copyToClipboard', 'Copied')}</>) : (<><Copy className="w-4 h-4 mr-1" />{t('notices.copyToClipboard', 'Copy')}</>)}
              </button>
            </div>

            {generatedNotice.reference_number && (
              <div className="px-5 py-3 bg-white/5 dark:bg-white/5 border-b border-night-border/40 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div><span className="text-mitti-500 dark:text-mitti-400">Ref: </span><span className="font-mono font-semibold text-mitti-900 dark:text-kora-100">{generatedNotice.reference_number}</span></div>
                <div><span className="text-mitti-500 dark:text-mitti-400">Type: </span><span className="capitalize text-mitti-900 dark:text-kora-100">{generatedNotice.notice_type}</span></div>
              </div>
            )}

            <div className="p-5">
              <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-mitti-900 dark:text-kora-100 bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-5 rounded-r-lg">
                {generatedNotice.formatted_notice}
              </pre>
            </div>

            <div className="border-t border-night-border/40 p-4 flex space-x-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSaveDraft}
                disabled={saving || saved}
                className="flex-1 py-2.5 bg-india-green-600 hover:bg-india-green-700 text-white rounded-lg font-medium disabled:bg-gray-400 flex items-center justify-center space-x-2 transition-all"
              >
                {saving ? <ThemedSpinner /> : saved ? (<><CheckCircle className="w-4 h-4" /><span>{t('notices.saveDraft', 'Saved!')}</span></>) : (<><Send className="w-4 h-4" /><span>{t('notices.saveDraft', 'Save as Draft')}</span></>)}
              </motion.button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="village-card rounded-xl border-2 border-dashed border-mitti-300/30 dark:border-mitti-700/20 p-12 text-center"
          >
            <FileText className="w-12 h-12 text-mitti-400/50 mx-auto mb-3" />
            <h3 className="font-semibold text-mitti-900 dark:text-kora-100 mb-1">No Notice Generated</h3>
            <p className="text-sm text-mitti-500 dark:text-mitti-400">Fill in the form and click "{t('notices.generateNotice', 'Generate Notice')}"</p>
          </motion.div>
        )}
      </div>
    </div>
  );
};

/* ============================================================
   VIEW MODAL -- read-only formatted notice viewer
   ============================================================ */
interface ViewModalProps {
  notice: any;
  onClose: () => void;
}

const ViewModal: React.FC<ViewModalProps> = ({ notice, onClose }) => {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const content = notice.formatted_notice || notice.body || '';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: 'spring', damping: 25 }}
        className="village-card rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
      >
        <div className="bg-gradient-to-r from-mitti-500 to-haldi-500 p-5 text-white flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="font-bold flex items-center"><Eye className="w-5 h-5 mr-2" />{t('notices.viewNotice', 'View Notice')}</h2>
            <p className="text-sm text-white/80 mt-1">{notice.notice_id || notice.reference_number}</p>
          </div>
          <div className="flex items-center space-x-2">
            <button onClick={handleCopy} className="px-3 py-1.5 bg-white/20 rounded-lg text-sm hover:bg-mitti-100/50 flex items-center transition-all">
              {copied ? (<><CheckCircle className="w-4 h-4 mr-1" />{t('notices.copyToClipboard', 'Copied')}</>) : (<><Copy className="w-4 h-4 mr-1" />{t('notices.copyToClipboard', 'Copy')}</>)}
            </button>
            <button onClick={onClose} className="p-2 bg-white/20 rounded-lg hover:bg-mitti-100/50 transition-all"><X className="w-5 h-5" /></button>
          </div>
        </div>

        <div className="px-6 py-4 bg-white/5 dark:bg-white/5 border-b border-night-border/40 flex-shrink-0">
          <h3 className="font-semibold text-mitti-900 dark:text-kora-100 text-lg">{notice.subject || notice.scheme_name}</h3>
          <div className="flex items-center space-x-4 mt-2 text-sm text-mitti-500 dark:text-mitti-400 flex-wrap gap-1">
            <span className="capitalize">{notice.notice_type}</span>
            {notice.effective_date && <span><Calendar className="w-3 h-3 inline mr-1" />Effective: {notice.effective_date}</span>}
            {notice.created_at && <span><Clock className="w-3 h-3 inline mr-1" />{new Date(notice.created_at).toLocaleDateString()}</span>}
          </div>
        </div>

        <div className="p-6 overflow-y-auto flex-1" data-lenis-prevent>
          {notice.formatted_notice ? (
            <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-mitti-900 dark:text-kora-100 bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-5 rounded-r-lg">
              {notice.formatted_notice}
            </pre>
          ) : notice.body ? (
            <div className="prose dark:prose-invert max-w-none">
              <p className="text-mitti-700 dark:text-mitti-300 whitespace-pre-wrap">{notice.body}</p>
            </div>
          ) : (
            <p className="text-mitti-500 italic text-center py-8">No notice content available.</p>
          )}
        </div>

        <div className="border-t border-night-border/40 p-4 flex-shrink-0">
          <button onClick={onClose}
            className="w-full py-2.5 village-input rounded-lg text-mitti-700 dark:text-mitti-300 font-medium hover:bg-white/10 transition-all">
            {t('common.close', 'Close')}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

/* ============================================================
   EDIT MODAL -- edit subject, body, formatted_notice, date
   ============================================================ */
interface EditModalProps {
  notice: any;
  onClose: () => void;
  onSaved: () => void;
}

const EditModal: React.FC<EditModalProps> = ({ notice, onClose, onSaved }) => {
  const { t } = useTranslation();
  const [subject, setSubject] = useState(notice.subject || '');
  const [body, setBody] = useState(notice.body || '');
  const [formattedNotice, setFormattedNotice] = useState(notice.formatted_notice || '');
  const [effectiveDate, setEffectiveDate] = useState(
    notice.effective_date ? notice.effective_date.split('T')[0] : ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editTab, setEditTab] = useState<'formatted' | 'body'>('formatted');

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiService.updateNotice(notice.notice_id, {
        subject,
        body,
        formatted_notice: formattedNotice,
        effective_date: effectiveDate || undefined,
      });
      onSaved();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: 'spring', damping: 25 }}
        className="village-card rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
      >
        <div className="bg-gradient-to-r from-mitti-500 to-haldi-500 p-5 text-white flex items-center justify-between flex-shrink-0">
          <h2 className="font-bold flex items-center"><Edit2 className="w-5 h-5 mr-2" />{t('notices.editNotice', 'Edit Notice')}</h2>
          <button onClick={onClose} className="p-2 bg-white/20 rounded-lg hover:bg-mitti-100/50 transition-all"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4" data-lenis-prevent>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('notices.subject', 'Subject')}</label>
            <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)}
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
          </div>

          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">Notice Content</label>
            <div className="flex space-x-2 mb-2">
              <button onClick={() => setEditTab('formatted')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${editTab === 'formatted' ? 'bg-mitti-500 text-white shadow-md' : 'village-input text-mitti-600 dark:text-mitti-300'}`}>
                {t('notices.formattedNotice', 'Formatted Notice')}
              </button>
              <button onClick={() => setEditTab('body')}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${editTab === 'body' ? 'bg-mitti-500 text-white shadow-md' : 'village-input text-mitti-600 dark:text-mitti-300'}`}>
                {t('notices.bodyText', 'Body Text')}
              </button>
            </div>
            {editTab === 'formatted' ? (
              <textarea value={formattedNotice} onChange={(e) => setFormattedNotice(e.target.value)}
                rows={14}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500 resize-y font-mono text-sm" />
            ) : (
              <textarea value={body} onChange={(e) => setBody(e.target.value)}
                rows={14}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500 resize-y font-mono text-sm" />
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('notices.effectiveDate', 'Effective Date')}</label>
            <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)}
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start space-x-2"
            >
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </motion.div>
          )}
        </div>

        <div className="border-t border-night-border/40 p-4 flex space-x-3 flex-shrink-0">
          <button onClick={onClose}
            className="flex-1 py-2.5 village-input rounded-lg text-mitti-700 dark:text-mitti-300 font-medium hover:bg-white/10 transition-all">
            {t('common.cancel', 'Cancel')}
          </button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2.5 btn-mitti bg-mitti-500 text-white rounded-lg font-medium hover:bg-mitti-600 disabled:opacity-50 flex items-center justify-center space-x-2 transition-all"
          >
            {saving ? (<><ThemedSpinner /><span>Saving...</span></>) : (<><CheckCircle className="w-4 h-4" /><span>Save Changes</span></>)}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
};

/* ============================================================
   DRAFTS TAB
   ============================================================ */
const DraftsTab: React.FC = () => {
  const { t } = useTranslation();
  const [notices, setNotices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingNotice, setEditingNotice] = useState<any>(null);
  const [viewingNotice, setViewingNotice] = useState<any>(null);
  const [publishing, setPublishing] = useState<string | null>(null);

  useEffect(() => { loadDrafts(); }, []);

  const loadDrafts = async () => {
    setLoading(true);
    try {
      const data = await apiService.listNotices('draft');
      setNotices(data.notices || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const handlePublish = async (noticeId: string) => {
    if (!confirm('Publish this notice directly to the Public Board?')) return;
    setPublishing(noticeId);
    try {
      await apiService.publishNotice(noticeId);
      loadDrafts();
    } catch {
      toast.error('Failed to publish notice');
    } finally {
      setPublishing(null);
    }
  };

  const handleSubmitReview = async (noticeId: string) => {
    try {
      await apiService.submitNoticeForReview(noticeId);
      loadDrafts();
    } catch {
      toast.error('Failed to submit for review');
    }
  };

  const handleDelete = async (noticeId: string) => {
    if (!confirm('Delete this draft?')) return;
    try {
      await apiService.deleteNotice(noticeId);
      loadDrafts();
    } catch {
      toast.error('Failed to delete');
    }
  };

  if (loading) return (
    <div className="text-center py-12"><ThemedSpinner /></div>
  );

  if (notices.length === 0) return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="village-card rounded-xl p-12 text-center"
    >
      <FileText className="w-12 h-12 text-mitti-400/50 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('notices.noDrafts', 'No drafts yet. Generate a notice first.')}</p>
    </motion.div>
  );

  return (
    <>
      <div className="space-y-4">
        {notices.map((n: any, index: number) => (
          <motion.div
            key={n.notice_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
            className="village-card rounded-xl p-5"
          >
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-3 mb-1 flex-wrap gap-1">
                  <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400">{n.notice_id || n.reference_number}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                    {n.status?.toUpperCase() || 'DRAFT'}
                  </span>
                  <span className="text-xs text-mitti-500 capitalize">{n.notice_type}</span>
                </div>
                <h3 className="font-semibold text-mitti-900 dark:text-kora-100">{n.subject || n.scheme_name}</h3>
                {n.review_notes && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                  >
                    <p className="text-xs font-semibold text-red-700 dark:text-red-400 mb-0.5 flex items-center">
                      <XCircle className="w-3.5 h-3.5 mr-1" />{t('notices.rejectedByAdmin', 'Rejected by Admin')}
                      {n.reviewed_at && <span className="font-normal ml-2 text-red-500">({new Date(n.reviewed_at).toLocaleDateString()})</span>}
                    </p>
                    <p className="text-sm text-red-600 dark:text-red-300">{n.review_notes}</p>
                  </motion.div>
                )}
                {!n.review_notes && n.body && (
                  <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-1 line-clamp-2">{n.body}</p>
                )}
                <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-1">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {n.created_at ? new Date(n.created_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0 flex-wrap gap-1">
                <button onClick={() => setViewingNotice(n)}
                  className="px-3 py-2 village-input rounded-lg text-sm font-medium hover:bg-white/10 flex items-center space-x-1 transition-all">
                  <Eye className="w-4 h-4" /><span>{t('notices.viewNotice', 'View')}</span>
                </button>
                <button onClick={() => setEditingNotice(n)}
                  className="px-3 py-2 village-input rounded-lg text-sm font-medium hover:bg-white/10 flex items-center space-x-1 transition-all">
                  <Edit2 className="w-4 h-4" /><span>{t('notices.editNotice', 'Edit')}</span>
                </button>
                <button onClick={() => handlePublish(n.notice_id)} disabled={publishing === n.notice_id}
                  className="px-3 py-2 bg-india-green-600 hover:bg-india-green-700 text-white rounded-lg text-sm font-medium disabled:bg-gray-400 flex items-center space-x-1 transition-all">
                  {publishing === n.notice_id ? <ThemedSpinner /> : <Globe className="w-4 h-4" />}
                  <span>{t('notices.publish', 'Publish')}</span>
                </button>
                <button onClick={() => handleSubmitReview(n.notice_id)}
                  className="px-3 py-2 btn-mitti bg-mitti-500 hover:bg-mitti-600 text-white rounded-lg text-sm font-medium flex items-center space-x-1 transition-all">
                  <Send className="w-4 h-4" /><span>{t('notices.submitReview', 'Submit for Review')}</span>
                </button>
                <button onClick={() => handleDelete(n.notice_id)}
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all">
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <AnimatePresence>
        {viewingNotice && <ViewModal notice={viewingNotice} onClose={() => setViewingNotice(null)} />}
        {editingNotice && <EditModal notice={editingNotice} onClose={() => setEditingNotice(null)} onSaved={() => { setEditingNotice(null); loadDrafts(); }} />}
      </AnimatePresence>
    </>
  );
};

/* ============================================================
   REVIEW TAB (admin only)
   ============================================================ */
const ReviewTab: React.FC = () => {
  const { t } = useTranslation();
  const [notices, setNotices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [viewingNotice, setViewingNotice] = useState<any>(null);
  const [rejectModal, setRejectModal] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => { loadPendingReview(); }, []);

  const loadPendingReview = async () => {
    setLoading(true);
    try {
      const data = await apiService.listNotices('pending_review');
      setNotices(data.notices || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const handleApprove = async (noticeId: string) => {
    setProcessing(noticeId);
    try {
      await apiService.reviewNotice(noticeId, true);
      await apiService.publishNotice(noticeId);
      loadPendingReview();
    } catch {
      toast.error('Failed to approve and publish notice');
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async () => {
    if (!rejectModal || !rejectReason.trim()) return;
    setProcessing(rejectModal);
    try {
      await apiService.reviewNotice(rejectModal, false, rejectReason.trim());
      setRejectModal(null);
      setRejectReason('');
      loadPendingReview();
    } catch {
      toast.error('Failed to reject notice');
    } finally {
      setProcessing(null);
    }
  };

  if (loading) return (
    <div className="text-center py-12"><ThemedSpinner /></div>
  );

  if (notices.length === 0) return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="village-card rounded-xl p-12 text-center"
    >
      <ShieldCheck className="w-12 h-12 text-mitti-400/50 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('notices.noPendingReview', 'No notices pending review.')}</p>
    </motion.div>
  );

  return (
    <>
      <div className="space-y-4">
        {notices.map((n: any, index: number) => {
          const isProcessing = processing === n.notice_id;
          return (
            <motion.div
              key={n.notice_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="village-card rounded-xl p-5"
            >
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-3 mb-1 flex-wrap gap-1">
                    <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400">{n.notice_id || n.reference_number}</span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">PENDING REVIEW</span>
                    <span className="text-xs text-mitti-500 capitalize">{n.notice_type}</span>
                  </div>
                  <h3 className="font-semibold text-mitti-900 dark:text-kora-100">{n.subject || n.scheme_name}</h3>
                  {n.body && <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-1 line-clamp-2">{n.body}</p>}
                  <div className="flex items-center space-x-4 mt-2 text-xs text-mitti-500 dark:text-mitti-400 flex-wrap gap-1">
                    {n.officer_name && <span>By: {n.officer_name}</span>}
                    {n.created_at && <span><Clock className="w-3 h-3 inline mr-1" />{new Date(n.created_at).toLocaleDateString()}</span>}
                    {n.effective_date && <span><Calendar className="w-3 h-3 inline mr-1" />Effective: {new Date(n.effective_date).toLocaleDateString()}</span>}
                  </div>
                </div>
                <div className="flex items-center space-x-2 flex-shrink-0">
                  <button onClick={() => setViewingNotice(n)}
                    className="px-3 py-2 village-input rounded-lg text-sm font-medium hover:bg-white/10 flex items-center space-x-1 transition-all">
                    <Eye className="w-4 h-4" /><span>{t('notices.viewNotice', 'View')}</span>
                  </button>
                  {isProcessing ? (
                    <ThemedSpinner />
                  ) : (
                    <>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handleApprove(n.notice_id)}
                        className="px-4 py-2 bg-india-green-600 hover:bg-india-green-700 text-white rounded-lg text-sm font-medium flex items-center space-x-1 transition-all"
                      >
                        <CheckCircle className="w-4 h-4" /><span>{t('notices.approve', 'Approve & Publish')}</span>
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => { setRejectModal(n.notice_id); setRejectReason(''); }}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 flex items-center space-x-1 transition-all"
                      >
                        <XCircle className="w-4 h-4" /><span>{t('notices.rejectNotice', 'Reject')}</span>
                      </motion.button>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      <AnimatePresence>
        {viewingNotice && <ViewModal notice={viewingNotice} onClose={() => setViewingNotice(null)} />}
      </AnimatePresence>

      {/* Reject Modal */}
      <AnimatePresence>
        {rejectModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 25 }}
              className="village-card rounded-xl max-w-md w-full shadow-2xl overflow-hidden"
            >
              <div className="bg-gradient-to-r from-red-600 to-red-700 p-5 text-white">
                <h2 className="font-bold flex items-center"><XCircle className="w-5 h-5 mr-2" />{t('notices.rejectNotice', 'Reject Notice')}</h2>
                <p className="text-sm text-red-100 mt-1">This notice will be sent back to the officer as a draft with your feedback.</p>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">Rejection Reason *</label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    rows={4}
                    placeholder="Explain what needs to be fixed (e.g., incorrect scheme name, wrong dates, missing information...)"
                    className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-red-500 text-sm"
                    autoFocus
                  />
                </div>
              </div>
              <div className="border-t border-night-border/40 p-4 flex space-x-3">
                <button onClick={() => { setRejectModal(null); setRejectReason(''); }}
                  className="flex-1 py-2.5 village-input rounded-lg text-mitti-700 dark:text-mitti-300 font-medium hover:bg-white/10 transition-all">
                  {t('common.cancel', 'Cancel')}
                </button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleReject}
                  disabled={!rejectReason.trim() || processing === rejectModal}
                  className="flex-1 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 flex items-center justify-center space-x-2 transition-all"
                >
                  {processing === rejectModal ? (<><ThemedSpinner /><span>Rejecting...</span></>) : (<><XCircle className="w-4 h-4" /><span>{t('notices.rejectNotice', 'Reject Notice')}</span></>)}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

/* ============================================================
   PUBLISHED TAB
   ============================================================ */
const PublishedTab: React.FC = () => {
  const { t } = useTranslation();
  const [notices, setNotices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewingNotice, setViewingNotice] = useState<any>(null);

  useEffect(() => { loadPublished(); }, []);

  const loadPublished = async () => {
    setLoading(true);
    try {
      const data = await apiService.listNotices('published');
      setNotices(data.notices || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const handleWithdraw = async (noticeId: string) => {
    const reason = prompt('Reason for withdrawal:');
    if (!reason) return;
    try {
      await apiService.withdrawNotice(noticeId, reason);
      loadPublished();
    } catch {
      toast.error('Failed to withdraw');
    }
  };

  if (loading) return (
    <div className="text-center py-12"><ThemedSpinner /></div>
  );

  if (notices.length === 0) return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="village-card rounded-xl p-12 text-center"
    >
      <FileText className="w-12 h-12 text-mitti-400/50 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('notices.noPublished', 'No published notices.')}</p>
    </motion.div>
  );

  return (
    <>
      <div className="space-y-4">
        {notices.map((n: any, index: number) => (
          <motion.div
            key={n.notice_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
            className="village-card rounded-xl p-5"
          >
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div>
                <div className="flex items-center space-x-3 mb-1 flex-wrap gap-1">
                  <span className="font-mono text-sm text-mitti-500 dark:text-mitti-400">{n.notice_id}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">PUBLISHED</span>
                  <span className="text-xs text-mitti-500 capitalize">{n.notice_type}</span>
                </div>
                <h3 className="font-semibold text-mitti-900 dark:text-kora-100">{n.subject || n.scheme_name}</h3>
                <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-1">
                  Views: {n.view_count || 0} &middot; Published: {n.published_at ? new Date(n.published_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0">
                <button onClick={() => setViewingNotice(n)}
                  className="px-3 py-2 village-input rounded-lg text-sm font-medium hover:bg-white/10 flex items-center space-x-1 transition-all">
                  <Eye className="w-4 h-4" /><span>{t('notices.viewNotice', 'View')}</span>
                </button>
                <button onClick={() => handleWithdraw(n.notice_id)}
                  className="px-3 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-all">Withdraw</button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <AnimatePresence>
        {viewingNotice && <ViewModal notice={viewingNotice} onClose={() => setViewingNotice(null)} />}
      </AnimatePresence>
    </>
  );
};

/* ============================================================
   PUBLIC BOARD TAB
   ============================================================ */
const NOTICE_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'circular', label: 'Circular' },
  { value: 'memo', label: 'Memorandum' },
  { value: 'order', label: 'Government Order' },
  { value: 'notification', label: 'Notification' },
  { value: 'advisory', label: 'Advisory' },
  { value: 'amendment', label: 'Amendment' },
];

const PublicBoardTab: React.FC = () => {
  const { t } = useTranslation();
  const [notices, setNotices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNotice, setSelectedNotice] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  useEffect(() => { loadPublicNotices(); }, []);

  const loadPublicNotices = async () => {
    setLoading(true);
    try {
      const data = await apiService.getPublicNotices();
      setNotices(data.notices || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const viewNotice = async (noticeId: string) => {
    try {
      const data = await apiService.getPublicNoticeDetail(noticeId);
      setSelectedNotice(data);
    } catch {
      toast.error('Failed to load notice');
    }
  };

  const filteredNotices = notices.filter((n) => {
    const matchesSearch = searchQuery === '' ||
      (n.subject || n.scheme_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.notice_type || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === '' || n.notice_type === typeFilter;
    return matchesSearch && matchesType;
  });

  if (loading) return (
    <div className="text-center py-12"><ThemedSpinner /></div>
  );

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-mitti-400" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notices by subject or type..."
            className="village-input w-full pl-10 pr-4 py-2.5 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500 text-sm" />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-mitti-400 hover:text-mitti-600">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="relative sm:w-52">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-mitti-400" />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="village-input w-full pl-10 pr-4 py-2.5 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500 text-sm appearance-none">
            {NOTICE_TYPE_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
      </div>

      {filteredNotices.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="village-card rounded-xl p-12 text-center"
        >
          <FileText className="w-12 h-12 text-mitti-400/50 mx-auto mb-3" />
          <p className="text-mitti-600 dark:text-mitti-400">
            {notices.length === 0 ? 'No public notices available.' : 'No notices match your search or filter.'}
          </p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNotices.map((n: any, index: number) => (
            <motion.div
              key={n.notice_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.06 }}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              onClick={() => viewNotice(n.notice_id)}
              className="village-card rounded-xl p-5 hover:shadow-lg transition-all cursor-pointer"
            >
              <div className="flex items-center space-x-2 mb-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-mitti-100 text-mitti-600 dark:bg-mitti-800/20 dark:text-mitti-400 capitalize">{n.notice_type}</span>
                <span className="text-xs text-mitti-500 dark:text-mitti-400">{n.published_at ? new Date(n.published_at).toLocaleDateString() : ''}</span>
              </div>
              <h3 className="font-semibold text-mitti-900 dark:text-kora-100 mb-1">{n.subject || n.scheme_name}</h3>
              <p className="text-sm text-mitti-500 dark:text-mitti-400">Views: {n.view_count || 0}</p>
            </motion.div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedNotice && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 25 }}
              className="village-card rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden shadow-2xl"
            >
              <div className="bg-gradient-to-r from-mitti-500 to-haldi-500 p-5 text-white flex items-center justify-between flex-shrink-0">
                <h2 className="font-bold">{selectedNotice.subject || selectedNotice.scheme_name}</h2>
                <button onClick={() => setSelectedNotice(null)} className="p-2 bg-white/20 rounded-lg hover:bg-mitti-100/50 transition-all"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-6 overflow-y-auto flex-1" data-lenis-prevent>
                {selectedNotice.formatted_notice ? (
                  <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-mitti-900 dark:text-kora-100 bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-5 rounded-r-lg">
                    {selectedNotice.formatted_notice}
                  </pre>
                ) : selectedNotice.body ? (
                  <p className="text-mitti-700 dark:text-mitti-300 whitespace-pre-wrap">{selectedNotice.body}</p>
                ) : null}
              </div>
              <div className="border-t border-night-border/40 p-4 flex-shrink-0">
                <button onClick={() => setSelectedNotice(null)}
                  className="w-full py-2.5 village-input rounded-lg text-mitti-700 dark:text-mitti-300 font-medium hover:bg-white/10 transition-all">
                  {t('common.close', 'Close')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default NoticeDrafter;
