import React, { useState, useEffect, useRef } from 'react';
import {
  FileText, Search, Eye, X, Upload, Trash2, Clock,
  CheckCircle, Phone, AlignLeft, BookOpen, Pencil, MoreVertical,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import AnimatedModal from '../components/ui/AnimatedModal';
import SchemeDocumentViewer, { FormattedDoc } from '../components/ui/SchemeDocumentViewer';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import apiService from '../services/api';

const Schemes: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const role = user?.role || 'citizen';
  const canUpload = role === 'officer' || role === 'admin';

  const [activeTab, setActiveTab] = useState('browse');
  const tabs = canUpload
    ? [
        { id: 'browse', label: t('schemes.browseTab', 'Browse') },
        { id: 'upload', label: t('schemes.uploadTab', 'Upload') },
        { id: 'my', label: t('schemes.mySchemesTab', 'My Schemes') },
      ]
    : [{ id: 'browse', label: t('schemes.browseTab', 'Browse') }];

  return (
    <PageTransition>
      <div className="p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl md:text-3xl font-bold font-display text-kora-100 tracking-tight mb-1">
              {t('schemes.title', 'Government Schemes')}
            </h1>
            <p className="text-sm text-mitti-500/40">
              {t('schemes.subtitle', 'Explore and manage government welfare programs')}
            </p>
          </div>

          {tabs.length > 1 && (
            <div className="flex space-x-2 mb-6 village-card p-2 rounded-xl inline-flex">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-5 py-2 rounded-lg font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-mitti-500 text-white shadow-lg'
                      : 'text-mitti-600 dark:text-mitti-400 hover:bg-mitti-100 dark:hover:bg-night-bg'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {activeTab === 'browse' && <BrowseTab />}
          {activeTab === 'upload' && <UploadTab />}
          {activeTab === 'my' && <MySchemesTab />}
        </div>
      </div>
    </PageTransition>
  );
};

/* ===================== BROWSE TAB ===================== */

interface SummaryData {
  one_line_purpose?: string;
  eligibility?: string[];
  benefits?: string[];
  application_steps?: string[];
  contact_info?: string | string[];
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' as const },
  }),
};

interface SchemeItem {
  name: string;
  scheme_id?: string;
}

const BrowseTab: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [schemes, setSchemes] = useState<SchemeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedScheme, setSelectedScheme] = useState<string | null>(null);

  // Summary state
  const [summarizing, setSummarizing] = useState(false);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [summaryError, setSummaryError] = useState('');
  const [summaryLanguage, setSummaryLanguage] = useState<'en' | 'hi'>('en');

  // Full document state
  const [modalTab, setModalTab] = useState<'summary' | 'document'>('summary');
  const [fullDocument, setFullDocument] = useState<string>('');
  const [formattedDoc, setFormattedDoc] = useState<FormattedDoc | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState('');

  // Admin edit state
  const [editingScheme, setEditingScheme] = useState<SchemeItem | null>(null);
  const [editName, setEditName] = useState('');
  const [saving, setSaving] = useState(false);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);

  useEffect(() => { loadSchemes(); }, []);

  // Auto-trigger English summary whenever a scheme is selected
  useEffect(() => {
    if (selectedScheme) {
      setSummaryData(null);
      setSummaryError('');
      setSummaryLanguage('en');
      setModalTab('summary');
      setFullDocument('');
      setDocError('');
      handleSummarize(selectedScheme, 'en');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedScheme]);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = () => setMenuOpen(null);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [menuOpen]);

  const loadSchemes = async () => {
    try {
      // For admin, use detailed=true to get scheme_ids alongside names
      const response = isAdmin
        ? await apiService.listSchemesDetailed()
        : await apiService.listSchemes();

      const names: string[] = response.schemes || [];
      const idMap: Record<string, string> = response.scheme_ids || {};

      setSchemes(names.map((name: string) => ({
        name,
        scheme_id: idMap[name],
      })));
    } catch {
      setSchemes([{ name: 'PM-KISAN' }, { name: 'MGNREGA' }, { name: 'PMAY-G' }]);
    } finally { setLoading(false); }
  };

  const handleRename = async () => {
    if (!editingScheme?.scheme_id || !editName.trim()) return;
    setSaving(true);
    try {
      await apiService.updateSchemeMetadata(editingScheme.scheme_id, { scheme_name: editName.trim() });
      toast.success('Scheme renamed successfully');
      setEditingScheme(null);
      loadSchemes();
    } catch {
      toast.error('Failed to rename scheme');
    } finally { setSaving(false); }
  };

  const handleDelete = async (scheme: SchemeItem) => {
    if (!scheme.scheme_id) {
      toast.error('Cannot delete: scheme has no ID in metadata');
      return;
    }
    if (!confirm(`Are you sure you want to delete "${scheme.name}"? This action will archive the scheme.`)) return;
    try {
      await apiService.deleteScheme(scheme.scheme_id);
      toast.success('Scheme deleted');
      loadSchemes();
    } catch {
      toast.error('Failed to delete scheme');
    }
  };

  const handleSummarize = async (schemeName: string, language: 'en' | 'hi') => {
    setSummarizing(true);
    setSummaryData(null);
    setSummaryError('');
    setSummaryLanguage(language);
    try {
      const response = await apiService.summarizeScheme(schemeName, language);
      if (response && typeof response === 'object') {
        setSummaryData(response as SummaryData);
      } else {
        setSummaryError('Summary not available.');
      }
    } catch {
      setSummaryError('Failed to generate summary. Please try again.');
    } finally { setSummarizing(false); }
  };

  const handleLoadDocument = async (schemeName: string) => {
    if (fullDocument || formattedDoc) return;
    setDocLoading(true);
    setDocError('');

    // Try the LLM-formatted endpoint first (structured, elegant output)
    try {
      const response = await apiService.getSchemeDocumentFormatted(schemeName);
      if (response?.formatted?.sections?.length) {
        setFormattedDoc(response.formatted as FormattedDoc);
        setDocLoading(false);
        return;
      }
    } catch (e) {
      console.warn('Formatted document fetch failed, falling back to raw:', e);
    }

    // Fallback to raw text
    try {
      const response = await apiService.getSchemeDocument(schemeName);
      if (typeof response === 'string') {
        setFullDocument(response);
      } else if (response && typeof response === 'object') {
        const text =
          response.content ||
          response.text ||
          response.document ||
          response.full_text ||
          JSON.stringify(response, null, 2);
        setFullDocument(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
      } else {
        setDocError('Document not available.');
      }
    } catch {
      setDocError('Failed to load full document.');
    } finally { setDocLoading(false); }
  };

  const handleModalTabSwitch = (tab: 'summary' | 'document') => {
    setModalTab(tab);
    if (tab === 'document' && selectedScheme && !fullDocument && !formattedDoc) {
      handleLoadDocument(selectedScheme);
    }
  };

  const handleCloseModal = () => {
    setSelectedScheme(null);
    setSummaryData(null);
    setSummaryError('');
    setFullDocument('');
    setFormattedDoc(null);
    setDocError('');
    setModalTab('summary');
  };

  const normalizeContactInfo = (info: string | string[] | undefined): string[] => {
    if (!info) return [];
    if (Array.isArray(info)) return info;
    return [info];
  };

  const filtered = schemes.filter(s => s.name.toLowerCase().includes(searchTerm.toLowerCase()));
  const colors = [
    'from-mitti-500 to-mitti-600',
    'from-neel-500 to-neel-600',
    'from-mitti-600 to-mitti-700',
    'from-mitti-400 to-mitti-500',
  ];

  if (loading) return (
    <div className="text-center py-12">
      <ThemedSpinner />
    </div>
  );

  return (
    <>
      {/* Search */}
      <div className="village-card rounded-xl shadow-sm p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
          <input
            type="text"
            placeholder={t('schemes.searchPlaceholder', 'Search schemes...')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-12 pr-4 py-3 village-input rounded-lg focus:ring-2 focus:ring-mitti-500"
          />
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
        <AnimatePresence>
          {filtered.map((scheme, index) => (
            <motion.div
              key={scheme.name}
              custom={index}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              exit="hidden"
              className="village-card rounded-xl shadow-sm overflow-hidden hover:shadow-lg transition-all"
            >
              <div className={`bg-gradient-to-r ${colors[index % colors.length]} p-3 md:p-5 text-white relative`}>
                <h3 className="text-xl font-bold font-display pr-8">{scheme.name}</h3>
                <p className="text-sm opacity-90 mt-1">Government Welfare Scheme</p>

                {/* Admin menu */}
                {isAdmin && scheme.scheme_id && (
                  <div className="absolute top-3 right-3">
                    <button
                      onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === scheme.scheme_id ? null : scheme.scheme_id!); }}
                      className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    {menuOpen === scheme.scheme_id && (
                      <div className="absolute right-0 top-9 bg-white dark:bg-night-card border border-mitti-200 dark:border-night-border rounded-xl shadow-xl z-20 min-w-[140px] overflow-hidden">
                        <button
                          onClick={(e) => { e.stopPropagation(); setMenuOpen(null); setEditingScheme(scheme); setEditName(scheme.name); }}
                          className="w-full flex items-center space-x-2 px-4 py-2.5 text-sm text-mitti-700 dark:text-kora-200 hover:bg-mitti-50 dark:hover:bg-night-bg transition-colors"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          <span>Rename</span>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setMenuOpen(null); handleDelete(scheme); }}
                          className="w-full flex items-center space-x-2 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="p-3 md:p-5">
                <button
                  onClick={() => setSelectedScheme(scheme.name)}
                  className="w-full py-2.5 bg-gradient-to-r from-mitti-500 to-mitti-600 text-white rounded-lg hover:shadow-lg transition-all font-medium flex items-center justify-center space-x-2"
                >
                  <Eye className="w-4 h-4" />
                  <span>{t('schemes.viewDetails', 'View Details')}</span>
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Rename Modal (Admin) */}
      <AnimatedModal isOpen={!!editingScheme} onClose={() => setEditingScheme(null)} maxWidth="max-w-md">
        <div className="village-card rounded-xl p-6 max-w-md w-full shadow-2xl">
          <h3 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4">Rename Scheme</h3>
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            className="w-full px-4 py-3 village-input rounded-lg focus:ring-2 focus:ring-mitti-500 mb-4"
            placeholder="Scheme name"
            autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') handleRename(); }}
          />
          <div className="flex space-x-3">
            <button
              onClick={() => setEditingScheme(null)}
              className="flex-1 py-2.5 border border-mitti-300 dark:border-night-border rounded-lg text-mitti-700 dark:text-kora-200 font-medium hover:bg-mitti-50 dark:hover:bg-night-bg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleRename}
              disabled={saving || !editName.trim() || editName.trim() === editingScheme?.name}
              className="flex-1 py-2.5 btn-mitti rounded-lg font-medium disabled:opacity-50 flex items-center justify-center"
            >
              {saving ? <ThemedSpinner size="sm" /> : 'Save'}
            </button>
          </div>
        </div>
      </AnimatedModal>

      {filtered.length === 0 && (
        <div className="text-center py-12 village-card rounded-xl">
          <Search className="w-10 h-10 text-mitti-400 mx-auto mb-3" />
          <p className="text-mitti-500 dark:text-mitti-400">{t('schemes.noSchemes', 'No schemes found')}</p>
          <button
            onClick={() => setSearchTerm('')}
            className="mt-2 text-mitti-600 hover:text-mitti-700 font-medium text-sm"
          >
            Clear search
          </button>
        </div>
      )}

      {/* Detail Modal */}
      <AnimatedModal isOpen={!!selectedScheme} onClose={handleCloseModal} maxWidth="max-w-2xl">
        <div className="village-card rounded-xl max-w-2xl w-full max-h-[88vh] flex flex-col overflow-hidden shadow-2xl">

          {/* Modal Header */}
          <div className="bg-gradient-to-r from-mitti-500 to-mitti-600 p-5 text-white flex items-center justify-between flex-shrink-0">
            <div>
              <h2 className="text-xl font-bold font-display">{selectedScheme}</h2>
              <p className="text-sm opacity-90">Scheme Details</p>
            </div>
            <button
              onClick={handleCloseModal}
              className="p-2 bg-white/20 rounded-lg hover:bg-white/30 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Inner Tab Switcher: AI Summary / Full Document */}
          <div className="flex border-b border-mitti-200 dark:border-night-border bg-kora dark:bg-night-bg flex-shrink-0">
            <button
              onClick={() => handleModalTabSwitch('summary')}
              className={`flex items-center space-x-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                modalTab === 'summary'
                  ? 'border-mitti-600 text-mitti-600 dark:text-mitti-400'
                  : 'border-transparent text-mitti-500 dark:text-mitti-400 hover:text-mitti-700 dark:hover:text-kora-200'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>{t('schemes.aiSummary', 'AI Summary')}</span>
            </button>
            <button
              onClick={() => handleModalTabSwitch('document')}
              className={`flex items-center space-x-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                modalTab === 'document'
                  ? 'border-mitti-600 text-mitti-600 dark:text-mitti-400'
                  : 'border-transparent text-mitti-500 dark:text-mitti-400 hover:text-mitti-700 dark:hover:text-kora-200'
              }`}
            >
              <AlignLeft className="w-4 h-4" />
              <span>{t('schemes.fullDocument', 'Full Document')}</span>
            </button>
          </div>

          {/* Scrollable Body */}
          <div className="flex-1 overflow-y-auto" data-lenis-prevent>

            {/* ---- AI SUMMARY TAB ---- */}
            {modalTab === 'summary' && (
              <div className="p-3 md:p-5 space-y-4">

                {/* Language toggle header */}
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-mitti-600 dark:text-mitti-400">
                    Language:
                  </p>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleSummarize(selectedScheme!, 'en')}
                      disabled={summarizing}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                        summaryLanguage === 'en' && !summarizing
                          ? 'bg-mitti-600 text-white'
                          : 'bg-mitti-100 dark:bg-night-bg text-mitti-700 dark:text-kora-200 hover:bg-mitti-50 dark:hover:bg-mitti-900/30 hover:text-mitti-700 dark:hover:text-mitti-300'
                      }`}
                    >
                      {t('common.english', 'English')}
                    </button>
                    <button
                      onClick={() => handleSummarize(selectedScheme!, 'hi')}
                      disabled={summarizing}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                        summaryLanguage === 'hi' && !summarizing
                          ? 'bg-neel-600 text-white'
                          : 'bg-mitti-100 dark:bg-night-bg text-mitti-700 dark:text-kora-200 hover:bg-neel-50 dark:hover:bg-neel-900/30 hover:text-neel-700 dark:hover:text-neel-300'
                      }`}
                    >
                      {t('common.hindi', 'Hindi')}
                    </button>
                  </div>
                </div>

                {/* Loading state */}
                {summarizing && (
                  <div className="flex flex-col items-center justify-center space-y-3 py-12 text-mitti-500 dark:text-mitti-400">
                    <ThemedSpinner />
                    <span className="text-sm">{t('schemes.generating', 'Generating AI summary...')}</span>
                  </div>
                )}

                {/* Error state */}
                {!summarizing && summaryError && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
                    {summaryError}
                  </div>
                )}

                {/* Structured summary cards */}
                {!summarizing && summaryData && (
                  <div className="space-y-4">

                    {/* Purpose card - mitti tint */}
                    {summaryData.one_line_purpose && (
                      <div className="p-4 bg-mitti-50 dark:bg-mitti-900/20 border border-mitti-200 dark:border-mitti-800 rounded-xl">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-mitti-600 dark:text-mitti-400 mb-1">
                          {t('schemes.purpose', 'Purpose')}
                        </h4>
                        <p className="text-mitti-800 dark:text-kora-200 font-medium leading-relaxed">
                          {summaryData.one_line_purpose}
                        </p>
                      </div>
                    )}

                    {/* Eligibility card */}
                    {summaryData.eligibility && summaryData.eligibility.length > 0 && (
                      <div className="p-4 village-card rounded-xl">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-mitti-500 dark:text-mitti-400 mb-3">
                          {t('schemes.eligibility', 'Eligibility')}
                        </h4>
                        <ul className="space-y-2">
                          {summaryData.eligibility.map((item, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <CheckCircle className="w-4 h-4 text-mitti-500 mt-0.5 flex-shrink-0" />
                              <span className="text-sm text-mitti-700 dark:text-kora-200 leading-relaxed">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Benefits card - green tint */}
                    {summaryData.benefits && summaryData.benefits.length > 0 && (
                      <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-green-600 dark:text-green-400 mb-3">
                          {t('schemes.benefits', 'Benefits')}
                        </h4>
                        <ul className="space-y-2">
                          {summaryData.benefits.map((item, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                              <span className="text-sm text-mitti-700 dark:text-kora-200 leading-relaxed">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* How to Apply card - numbered steps */}
                    {summaryData.application_steps && summaryData.application_steps.length > 0 && (
                      <div className="p-4 village-card rounded-xl">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-mitti-500 dark:text-mitti-400 mb-3">
                          {t('schemes.howToApply', 'How to Apply')}
                        </h4>
                        <ol className="space-y-3">
                          {summaryData.application_steps.map((step, i) => (
                            <li key={i} className="flex items-start space-x-3">
                              <span className="flex-shrink-0 w-6 h-6 bg-mitti-100 dark:bg-mitti-900/40 text-mitti-700 dark:text-mitti-300 rounded-full text-xs font-bold flex items-center justify-center">
                                {i + 1}
                              </span>
                              <span className="text-sm text-mitti-700 dark:text-kora-200 leading-relaxed pt-0.5">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {/* Contact Info card */}
                    {summaryData.contact_info && normalizeContactInfo(summaryData.contact_info).length > 0 && (
                      <div className="p-4 village-card rounded-xl">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-mitti-500 dark:text-mitti-400 mb-3">
                          {t('schemes.contactInfo', 'Contact Information')}
                        </h4>
                        <ul className="space-y-2">
                          {normalizeContactInfo(summaryData.contact_info).map((item, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <Phone className="w-4 h-4 text-mitti-400 mt-0.5 flex-shrink-0" />
                              <span className="text-sm text-mitti-700 dark:text-kora-200 leading-relaxed">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ---- FULL DOCUMENT TAB ---- */}
            {modalTab === 'document' && (
              <div className="p-3 md:p-5">
                {docLoading && (
                  <div className="flex flex-col items-center justify-center space-y-3 py-12 text-mitti-500 dark:text-mitti-400">
                    <ThemedSpinner />
                    <span className="text-sm">{t('schemes.loadingDocument', 'Formatting document…')}</span>
                    <span className="text-xs text-mitti-400">First load may take a moment — results are cached.</span>
                  </div>
                )}
                {!docLoading && docError && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
                    {docError}
                  </div>
                )}
                {!docLoading && !docError && (formattedDoc || fullDocument) && (
                  <div className="bg-kora dark:bg-night-bg border border-mitti-200 dark:border-night-border rounded-lg p-5 md:p-6 overflow-y-auto max-h-[60vh]">
                    <SchemeDocumentViewer content={fullDocument} formatted={formattedDoc || undefined} />
                  </div>
                )}
                {!docLoading && !docError && !fullDocument && !formattedDoc && (
                  <p className="text-sm text-mitti-500 dark:text-mitti-400 italic text-center py-12">
                    No document content available.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Modal Footer */}
          <div className="border-t border-mitti-200 dark:border-night-border p-4 flex-shrink-0">
            <button
              onClick={handleCloseModal}
              className="w-full py-2.5 border border-mitti-300 dark:border-night-border rounded-lg text-mitti-700 dark:text-kora-200 font-medium hover:bg-mitti-50 dark:hover:bg-night-bg transition-colors"
            >
              {t('common.close', 'Close')}
            </button>
          </div>
        </div>
      </AnimatedModal>
    </>
  );
};

/* ===================== UPLOAD TAB ===================== */
const UploadTab: React.FC = () => {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [schemeName, setSchemeName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      const data = await apiService.uploadScheme(file, schemeName || undefined);
      setResult({ success: true, ...data });
      setFile(null);
      setSchemeName('');
    } catch (err: any) {
      setResult({ success: false, error: err.response?.data?.detail || 'Upload failed' });
    } finally { setUploading(false); }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="village-card rounded-xl shadow-sm p-6 space-y-5">
        <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100">
          {t('schemes.uploadScheme', 'Upload Scheme Document')}
        </h2>

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-mitti-300 dark:border-night-border rounded-xl p-4 md:p-8 text-center cursor-pointer hover:border-mitti-500 dark:hover:border-mitti-400 transition-colors"
        >
          <Upload className="w-10 h-10 text-mitti-400 mx-auto mb-3" />
          {file ? (
            <div>
              <p className="font-medium text-mitti-900 dark:text-kora-100">{file.name}</p>
              <p className="text-sm text-mitti-500">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <>
              <p className="text-mitti-600 dark:text-mitti-400 font-medium">
                {t('schemes.dragDrop', 'Drop file here or click to browse')}
              </p>
              <p className="text-xs text-mitti-500 mt-1">Supports TXT, PDF, DOCX (max 50MB)</p>
            </>
          )}
          <input ref={fileRef} type="file" accept=".txt,.pdf,.docx" className="hidden" onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])} />
        </div>

        {/* Scheme Name */}
        <div>
          <label className="block text-sm font-medium text-mitti-700 dark:text-kora-200 mb-1">
            {t('schemes.schemeName', 'Scheme Name (optional)')}
          </label>
          <input
            type="text"
            value={schemeName}
            onChange={(e) => setSchemeName(e.target.value)}
            placeholder="Auto-detected from filename if empty"
            className="w-full px-3 py-2 village-input rounded-lg focus:ring-2 focus:ring-mitti-500"
          />
        </div>

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full py-3 btn-mitti text-white rounded-lg font-semibold hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {uploading ? (
            <>
              <ThemedSpinner />
              <span>{t('schemes.uploading', 'Uploading & Processing...')}</span>
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              <span>{t('schemes.uploadButton', 'Upload Scheme')}</span>
            </>
          )}
        </button>

        {result && (
          <div className={`p-4 rounded-lg border ${result.success ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'}`}>
            {result.success ? (
              <div className="flex items-start space-x-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
                <div>
                  <p className="font-medium text-green-800 dark:text-green-300">Upload successful!</p>
                  {result.scheme_id && <p className="text-sm text-green-700 dark:text-green-400">Scheme ID: {result.scheme_id}</p>}
                  {result.chunks_created != null && <p className="text-sm text-green-700 dark:text-green-400">Chunks created: {result.chunks_created}</p>}
                </div>
              </div>
            ) : (
              <p className="text-red-700 dark:text-red-400">{result.error}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/* ===================== MY SCHEMES TAB ===================== */
const MySchemesTab: React.FC = () => {
  const { t } = useTranslation();
  const [schemes, setSchemes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadMySchemes(); }, []);

  const loadMySchemes = async () => {
    try {
      const data = await apiService.getMySchemes();
      setSchemes(data.schemes || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const handleDelete = async (schemeId: string) => {
    if (!confirm('Delete this scheme?')) return;
    try {
      await apiService.deleteScheme(schemeId);
      loadMySchemes();
    } catch { toast.error('Failed to delete'); }
  };

  if (loading) return (
    <div className="text-center py-12">
      <ThemedSpinner />
    </div>
  );

  if (schemes.length === 0) return (
    <div className="village-card rounded-xl p-12 text-center">
      <FileText className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">{t('schemes.noSchemes', 'No schemes uploaded yet.')}</p>
    </div>
  );

  return (
    <div className="space-y-4">
      {schemes.map((s: any, index: number) => (
        <motion.div
          key={s.scheme_id}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.06, duration: 0.35 }}
          className="village-card rounded-xl shadow-sm p-5"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-mitti-900 dark:text-kora-100">{s.scheme_name}</h3>
              <div className="flex space-x-4 text-sm text-mitti-500 dark:text-mitti-400 mt-1">
                <span>Version {s.current_version || 1}</span>
                <span><Clock className="w-3 h-3 inline mr-1" />{s.uploaded_at ? new Date(s.uploaded_at).toLocaleDateString() : 'N/A'}</span>
                <span>{s.chunk_count || 0} chunks</span>
              </div>
            </div>
            <button onClick={() => handleDelete(s.scheme_id)}
              className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default Schemes;
