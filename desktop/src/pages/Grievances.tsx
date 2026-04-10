import React, { useState, useEffect } from 'react';
import { AlertCircle, Send, CheckCircle, Clock, MessageSquare, Star, ChevronDown, ChevronUp, User, Check, X, Inbox, Briefcase } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
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
            <h1 className="text-3xl font-bold text-mitti-900 dark:text-kora-100 mb-2">{t('grievances.title', 'Grievances')}</h1>
            <p className="text-mitti-600 dark:text-mitti-400">
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
                className={`px-5 py-2 rounded-lg font-medium transition-all ${activeTab === tab.id ? 'bg-mitti-500 text-white shadow-lg' : 'text-mitti-600 dark:text-mitti-400 hover:bg-mitti-100/50 dark:hover:bg-night-card/50'}`}>
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
const SubmitTab: React.FC = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    title: '', description: '', category: '', language: 'en',
    citizen_name: '', citizen_phone: '', citizen_email: '', citizen_location: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.description.trim()) return;
    setIsSubmitting(true);
    setResult(null);
    try {
      const response = await apiService.submitGrievance({
        description: formData.description,
        title: formData.title || undefined,
        citizen_name: formData.citizen_name || undefined,
        citizen_phone: formData.citizen_phone || undefined,
        citizen_email: formData.citizen_email || undefined,
        citizen_location: formData.citizen_location || undefined,
        category: formData.category || undefined,
        language: formData.language,
      });
      setResult(response);
    } catch {
      setResult({ error: t('grievances.submitError', 'Failed to submit grievance. Please try again.') });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <motion.div className="lg:col-span-2" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <form onSubmit={handleSubmit} className="village-card rounded-xl p-6 space-y-5">
          <div className="flex space-x-3">
            {[{ val: 'en', label: 'English' }, { val: 'hi', label: 'Hindi' }].map(l => (
              <button key={l.val} type="button" onClick={() => setFormData({ ...formData, language: l.val })}
                className={`flex-1 py-2 rounded-lg font-medium transition-all ${formData.language === l.val ? 'bg-mitti-500 text-white' : 'bg-mitti-100 dark:bg-night-card text-mitti-600 dark:text-mitti-300'}`}>
                {l.label}
              </button>
            ))}
          </div>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('grievances.categoryLabel', 'Category')}</label>
            <select value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500">
              <option value="">{t('grievances.selectCategory', 'Select category...')}</option>
              {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('grievances.titleLabel', 'Title')}</label>
            <input type="text" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder={t('grievances.titlePlaceholder', 'Brief summary...')}
              className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('grievances.descriptionLabel', 'Description')} *</label>
            <div className="flex items-start gap-3">
              <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder={t('grievances.descriptionPlaceholder', 'Describe your issue in detail...')} rows={5} required
                className="village-input flex-1 px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500 resize-none" />
              <VoiceInputButton
                onTranscription={(text) => setFormData({ ...formData, description: formData.description ? formData.description + ' ' + text : text })}
                size="sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.nameLabel', 'Name')}</label>
              <input type="text" value={formData.citizen_name} onChange={(e) => setFormData({ ...formData, citizen_name: e.target.value })}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.phoneLabel', 'Phone')}</label>
              <input type="tel" value={formData.citizen_phone} onChange={(e) => setFormData({ ...formData, citizen_phone: e.target.value })}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.emailLabel', 'Email')}</label>
              <input type="email" value={formData.citizen_email} onChange={(e) => setFormData({ ...formData, citizen_email: e.target.value })}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.locationLabel', 'Location')}</label>
              <input type="text" value={formData.citizen_location} onChange={(e) => setFormData({ ...formData, citizen_location: e.target.value })}
                className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" />
            </div>
          </div>
          <button type="submit" disabled={!formData.description.trim() || isSubmitting}
            className="btn-mitti w-full py-3 rounded-lg font-semibold transition-all text-white hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2">
            {isSubmitting ? <><ThemedSpinner size="sm" /><span>{t('grievances.submitting', 'Submitting...')}</span></> : <><Send className="w-5 h-5" /><span>{t('grievances.submitButton', 'Submit Grievance')}</span></>}
          </button>
        </form>
      </motion.div>
      <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
        <div className="village-card rounded-xl p-6 sticky top-6">
          <h3 className="text-lg font-semibold text-mitti-900 dark:text-kora-100 mb-4">{t('grievances.resultTitle', 'Result')}</h3>
          {!result && !isSubmitting && (
            <div className="text-center py-8">
              <AlertCircle className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
              <p className="text-sm text-mitti-500 dark:text-mitti-400">{t('grievances.submitToSeeResults', 'Submit to see routing results')}</p>
            </div>
          )}
          {isSubmitting && (
            <div className="text-center py-8">
              <ThemedSpinner size="lg" className="mx-auto mb-3" />
              <p className="text-sm text-mitti-600 dark:text-mitti-400">{t('grievances.analyzing', 'Analyzing...')}</p>
            </div>
          )}
          {result && !result.error && (
            <div className="space-y-3">
              {result.grievance_id && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <p className="text-xs text-green-600 dark:text-green-400 font-semibold">{t('grievances.grievanceId', 'GRIEVANCE ID')}</p>
                  <p className="text-lg font-mono font-bold text-green-900 dark:text-green-300">{result.grievance_id}</p>
                </div>
              )}
              {result.department && (
                <div className="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                  <p className="text-xs text-purple-600 dark:text-purple-400 font-semibold">{t('grievances.routedTo', 'ROUTED TO')}</p>
                  <p className="font-bold text-purple-900 dark:text-purple-300">{result.department}</p>
                </div>
              )}
              {result.priority && (
                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                  <p className="text-xs text-orange-600 dark:text-orange-400 font-semibold">{t('grievances.priority', 'PRIORITY')}</p>
                  <p className="font-bold text-orange-900 dark:text-orange-300 uppercase">{result.priority}</p>
                </div>
              )}
              {result.routing_reasoning && (
                <div className="p-3 bg-mitti-50 dark:bg-mitti-800/20 border border-mitti-200 dark:border-mitti-700 rounded-lg">
                  <p className="text-xs text-mitti-500 dark:text-mitti-400 font-semibold mb-1">{t('grievances.aiReasoning', 'AI REASONING')}</p>
                  <p className="text-sm text-mitti-700 dark:text-mitti-300">{result.routing_reasoning}</p>
                </div>
              )}
              <div className="p-3 bg-mitti-50 dark:bg-mitti-800/20 border border-mitti-200 dark:border-mitti-700 rounded-lg">
                <CheckCircle className="w-5 h-5 text-mitti-500 dark:text-mitti-400 inline mr-2" />
                <span className="text-sm text-mitti-700 dark:text-mitti-400 font-medium">{t('grievances.submittedSuccessfully', 'Submitted successfully')}</span>
              </div>
            </div>
          )}
          {result?.error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-700 dark:text-red-400">{result.error}</p>
            </div>
          )}
        </div>
      </motion.div>
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

  return (
    <div className="space-y-4">
      {grievances.map((g: any, index: number) => {
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
                <h3 className="font-semibold text-mitti-900 dark:text-kora-100">{g.title || g.description?.slice(0, 80)}</h3>
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
                    <p className="text-mitti-700 dark:text-mitti-300">{g.description}</p>
                  </div>

                  {/* Officer & Resolution Info */}
                  {(g.assigned_officer_name || g.resolution_notes) && !isRejected && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {g.assigned_officer_name && (
                        <div className="p-3 bg-mitti-50 dark:bg-mitti-800/20 border border-mitti-200 dark:border-mitti-700 rounded-lg">
                          <p className="text-xs font-bold text-mitti-500 dark:text-mitti-400 uppercase mb-1">{t('grievances.assignedOfficer', 'Assigned Officer')}</p>
                          <p className="text-sm font-medium text-mitti-700 dark:text-mitti-300 flex items-center">
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
                      <p className="text-sm text-mitti-700 dark:text-mitti-300">{g.routing_reasoning}</p>
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
                                <span className="text-sm font-semibold text-mitti-900 dark:text-kora-100 capitalize">{tl.new_status?.replace('_', ' ')}</span>
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
                            <span className="text-xs font-medium text-mitti-700 dark:text-mitti-300 flex items-center">
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
                          className="village-input flex-1 px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500" />
                        <button onClick={() => handleAddComment(g.grievance_id)}
                          className="px-4 py-2 bg-mitti-500 text-white rounded-lg hover:bg-mitti-600 text-sm font-medium flex items-center">
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
                  className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500 mb-4" />
                <div className="flex justify-end space-x-3">
                  <button onClick={() => setRatingModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-mitti-700 dark:text-mitti-300 hover:bg-gray-50 dark:hover:bg-night-card/50">{t('common.cancel', 'Cancel')}</button>
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
                  <h3 className="font-semibold text-mitti-900 dark:text-kora-100 mb-1">{g.title || g.description?.slice(0, 100)}</h3>
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
                            <span className="text-xs font-medium text-mitti-700 dark:text-mitti-300">{c.author_name || 'User'} {c.author_role ? `(${c.author_role})` : ''}</span>
                            <span className="text-xs text-mitti-500">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                          </div>
                          <p className="text-sm text-mitti-800 dark:text-kora-200">{c.comment_text}</p>
                        </div>
                      ))}
                      {(comments[g.grievance_id] || []).length === 0 && <p className="text-xs text-mitti-500">{t('grievances.noComments', 'No comments yet.')}</p>}
                      <div className="flex space-x-2 mt-2">
                        <input type="text" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                          placeholder={t('grievances.addComment', 'Add a comment...')} onKeyDown={(e) => e.key === 'Enter' && handleAddComment(g.grievance_id)}
                          className="village-input flex-1 px-3 py-1.5 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500" />
                        <button onClick={() => handleAddComment(g.grievance_id)}
                          className="px-3 py-1.5 bg-mitti-500 text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.send', 'Send')}</button>
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
              <h3 className="text-lg font-bold text-mitti-900 dark:text-kora-100 mb-4">
                {actionModal.type === 'accept' ? t('grievances.acceptGrievance', 'Accept Grievance') : t('grievances.rejectGrievance', 'Reject Grievance')}
              </h3>
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                  <p className="text-xs text-mitti-500 dark:text-mitti-400 mb-1">{t('grievances.actingAs', 'Acting as')}</p>
                  <p className="font-semibold text-mitti-900 dark:text-kora-100">{officerName}</p>
                </div>
                {actionModal.type === 'accept' && (
                  <div>
                    <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.notesOptional', 'Notes (optional)')}</label>
                    <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" rows={3} placeholder={t('grievances.addNotesPlaceholder', 'Add notes...')} />
                  </div>
                )}
                {actionModal.type === 'reject' && (
                  <div>
                    <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('grievances.rejectionReason', 'Rejection Reason')} *</label>
                    <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                      className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500" rows={3} placeholder={t('grievances.rejectionReasonPlaceholder', 'Reason for rejection...')} />
                  </div>
                )}
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button onClick={() => { setActionModal(null); setFormData({ notes: '', reason: '' }); }}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-mitti-700 dark:text-mitti-300">{t('common.cancel', 'Cancel')}</button>
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
                <h3 className="font-semibold text-mitti-900 dark:text-kora-100 mb-1">{g.title || g.description?.slice(0, 80)}</h3>
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
                        className="px-3 py-2 bg-mitti-500 text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.inProgress', 'In Progress')}</button>
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
                          <span className="text-xs font-medium text-mitti-700 dark:text-mitti-300">{c.author_name || 'User'}</span>
                          <span className="text-xs text-mitti-500">{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                        </div>
                        <p className="text-sm text-mitti-800 dark:text-kora-200">{c.comment_text}</p>
                      </div>
                    ))}
                    {(comments[g.grievance_id] || []).length === 0 && <p className="text-xs text-mitti-500">{t('grievances.noComments', 'No comments yet.')}</p>}
                    <div className="flex space-x-2 mt-2">
                      <input type="text" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                        placeholder={t('grievances.addComment', 'Add comment...')} onKeyDown={(e) => e.key === 'Enter' && handleAddComment(g.grievance_id)}
                        className="village-input flex-1 px-3 py-1.5 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500" />
                      <button onClick={() => handleAddComment(g.grievance_id)}
                        className="px-3 py-1.5 bg-mitti-500 text-white rounded-lg text-sm font-medium hover:bg-mitti-600">{t('common.send', 'Send')}</button>
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
              <h3 className="text-lg font-bold text-mitti-900 dark:text-kora-100 mb-4">
                {actionModal.type === 'resolve' ? t('grievances.resolveGrievance', 'Resolve Grievance') : t('grievances.updateToInProgress', 'Update to In Progress')}
              </h3>
              <div className="space-y-4">
                <div className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                  <p className="text-xs text-mitti-500 mb-1">{t('grievances.actingAs', 'Acting as')}</p>
                  <p className="font-semibold text-mitti-900 dark:text-kora-100">{officerName}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">
                    {actionModal.type === 'resolve' ? t('grievances.resolutionNotesRequired', 'Resolution Notes *') : t('grievances.notes', 'Notes')}
                  </label>
                  <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} rows={3}
                    className="village-input w-full px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 focus:ring-2 focus:ring-mitti-500"
                    placeholder={actionModal.type === 'resolve' ? t('grievances.resolvePlaceholder', 'How was this resolved...') : t('grievances.addNotesPlaceholder', 'Add notes...')} />
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button onClick={() => setActionModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-mitti-700 dark:text-mitti-300">{t('common.cancel', 'Cancel')}</button>
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
          className="village-input px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500">
          <option value="">{t('grievances.allStatuses', 'All Statuses')}</option>
          <option value="pending">{t('common.pending', 'Pending')}</option>
          <option value="accepted">{t('common.accepted', 'Accepted')}</option>
          <option value="in_progress">{t('common.inProgress', 'In Progress')}</option>
          <option value="resolved">{t('common.resolved', 'Resolved')}</option>
          <option value="rejected">{t('common.rejected', 'Rejected')}</option>
        </select>
        <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}
          className="village-input px-3 py-2 rounded-lg text-mitti-900 dark:text-kora-100 text-sm focus:ring-2 focus:ring-mitti-500">
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
              <h3 className="font-semibold text-mitti-900 dark:text-kora-100 mb-1">{g.title || g.description?.slice(0, 100)}</h3>
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
                            <p className="text-sm text-mitti-700 dark:text-mitti-300 leading-relaxed">{detailData.description}</p>
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
          <p className="text-3xl font-bold text-mitti-900 dark:text-kora-100">{analytics.total || 0}</p>
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
          <h3 className="text-lg font-semibold text-mitti-900 dark:text-kora-100 mb-4">{t('grievances.byDepartment', 'By Department')}</h3>
          <div className="space-y-2">
            {Object.entries(analytics.by_department).map(([dept, count]: [string, any]) => (
              <div key={dept} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg">
                <span className="font-medium text-mitti-900 dark:text-kora-100 capitalize">{dept}</span>
                <span className="text-sm font-bold text-mitti-700 dark:text-mitti-300">{count}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {analytics.by_status && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="village-card rounded-xl p-6">
          <h3 className="text-lg font-semibold text-mitti-900 dark:text-kora-100 mb-4">{t('grievances.byStatus', 'By Status')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(analytics.by_status).map(([status, count]: [string, any]) => (
              <div key={status} className="p-3 bg-gray-50 dark:bg-night-card/50 rounded-lg text-center">
                <p className="text-xs text-mitti-500 dark:text-mitti-400 uppercase">{status}</p>
                <p className="text-xl font-bold text-mitti-900 dark:text-kora-100">{count}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Grievances;
