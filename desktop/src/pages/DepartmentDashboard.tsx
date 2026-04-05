import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, Check, X, Clock, User, Phone, TrendingUp, Shield, MessageSquare, Send, ChevronDown, ChevronUp, PlayCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import apiService from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';

interface Grievance {
  grievance_id: string;
  citizen_name: string;
  citizen_phone: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  submitted_at: string;
  routing_reasoning: string;
  estimated_resolution_days: number;
  assigned_officer_name?: string;
}

interface Comment {
  id: number;
  grievance_id: string;
  author_name: string;
  author_role: string;
  comment_text: string;
  comment_type: string;
  is_public: boolean;
  created_at: string;
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.4, ease: 'easeOut' as const },
  }),
};

const grievanceVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' as const } },
};

const DepartmentDashboard: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const department = user?.department || 'general';
  const officerName = user?.username || '';
  const [filter, setFilter] = useState('pending');
  const [grievances, setGrievances] = useState<Grievance[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [actionModal, setActionModal] = useState<{ type: string; grievanceId: string } | null>(null);
  const [formData, setFormData] = useState({ notes: '', reason: '', resolution: '' });

  // Comments state
  const [expandedGrievance, setExpandedGrievance] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, Comment[]>>({});
  const [commentsLoading, setCommentsLoading] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [commentIsPublic, setCommentIsPublic] = useState(true);
  const [sendingComment, setSendingComment] = useState(false);

  useEffect(() => {
    loadGrievances();
  }, [filter]);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await apiService.getDepartmentDashboard(department);
      setDashboardData(data);
    } catch {
      // ignore
    }
  };

  const loadGrievances = async () => {
    setLoading(true);
    try {
      const data = await apiService.getDepartmentGrievances(department, filter);
      setGrievances(data.grievances || []);
    } catch (error) {
      console.error('Failed to load grievances:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadComments = useCallback(async (grievanceId: string) => {
    setCommentsLoading(grievanceId);
    try {
      const data = await apiService.getGrievanceComments(grievanceId);
      setComments(prev => ({ ...prev, [grievanceId]: data.comments || [] }));
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setCommentsLoading(null);
    }
  }, []);

  const toggleExpand = (grievanceId: string) => {
    if (expandedGrievance === grievanceId) {
      setExpandedGrievance(null);
    } else {
      setExpandedGrievance(grievanceId);
      if (!comments[grievanceId]) {
        loadComments(grievanceId);
      }
    }
  };

  const handleSendComment = async (grievanceId: string) => {
    if (!newComment.trim()) return;
    setSendingComment(true);
    try {
      await apiService.addGrievanceComment(grievanceId, newComment.trim(), 'note', commentIsPublic);
      setNewComment('');
      loadComments(grievanceId);
    } catch {
      toast.error('Failed to send comment');
    } finally {
      setSendingComment(false);
    }
  };

  const handleAccept = async () => {
    if (!actionModal) return;
    setActionLoading(true);
    try {
      await apiService.acceptGrievance(actionModal.grievanceId, officerName, formData.notes || undefined);
      loadGrievances();
      loadDashboard();
      setActionModal(null);
      setFormData({ notes: '', reason: '', resolution: '' });
    } catch {
      toast.error('Failed to accept grievance');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!actionModal || !formData.reason) return;
    setActionLoading(true);
    try {
      await apiService.rejectGrievance(actionModal.grievanceId, officerName, formData.reason);
      loadGrievances();
      loadDashboard();
      setActionModal(null);
      setFormData({ notes: '', reason: '', resolution: '' });
    } catch {
      toast.error('Failed to reject grievance');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkInProgress = async (grievanceId: string) => {
    setActionLoading(true);
    try {
      await apiService.updateGrievanceStatus(grievanceId, 'in_progress', officerName, 'Case work started');
      loadGrievances();
      loadDashboard();
    } catch {
      toast.error('Failed to update status');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!actionModal || !formData.resolution) return;
    setActionLoading(true);
    try {
      await apiService.resolveGrievance(actionModal.grievanceId, officerName, formData.resolution);
      loadGrievances();
      loadDashboard();
      setActionModal(null);
      setFormData({ notes: '', reason: '', resolution: '' });
    } catch {
      toast.error('Failed to resolve grievance');
    } finally {
      setActionLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-300 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
      case 'high': return 'bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-700 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800';
      case 'low': return 'bg-green-100 text-green-700 border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
      default: return 'bg-mitti-100 text-mitti-700 border-mitti-300 dark:bg-night-card dark:text-mitti-300 dark:border-night-border';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gold-100 text-gold-700 dark:bg-gold-900/30 dark:text-gold-400';
      case 'accepted': return 'bg-mitti-100 text-mitti-700 dark:bg-mitti-900/30 dark:text-mitti-400';
      case 'in_progress': return 'bg-mitti-200 text-mitti-800 dark:bg-mitti-900/30 dark:text-mitti-300';
      case 'resolved': return 'bg-india-green-100 text-india-green-700 dark:bg-india-green-900/30 dark:text-india-green-400';
      default: return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  const stats = dashboardData?.by_status || dashboardData?.stats || {};
  const categoryData = dashboardData?.by_category ? Object.entries(dashboardData.by_category).map(([name, count]) => ({ name, count })) : [];

  const statCards = [
    {
      label: t('departmentDashboard.pendingCount', 'Pending'),
      value: stats.pending || 0,
      icon: <AlertCircle className="w-5 h-5 text-gold-600 dark:text-gold-400" />,
      iconBg: 'bg-gold-100 dark:bg-gold-900/30',
    },
    {
      label: t('departmentDashboard.totalActive', 'Active'),
      value: (stats.accepted || 0) + (stats.in_progress || 0),
      icon: <TrendingUp className="w-5 h-5 text-mitti-600 dark:text-mitti-400" />,
      iconBg: 'bg-mitti-100 dark:bg-mitti-900/30',
    },
    {
      label: t('departmentDashboard.acceptedCount', 'Resolved'),
      value: stats.resolved || 0,
      icon: <Check className="w-5 h-5 text-india-green-600 dark:text-india-green-400" />,
      iconBg: 'bg-india-green-100 dark:bg-india-green-900/30',
    },
    {
      label: t('departmentDashboard.inProgressCount', 'Total'),
      value: dashboardData?.total || Object.values(stats).reduce((a: number, b: any) => a + (Number(b) || 0), 0),
      icon: <Shield className="w-5 h-5 text-terracotta-600 dark:text-terracotta-400" />,
      iconBg: 'bg-terracotta-100 dark:bg-terracotta-900/30',
    },
  ];

  return (
    <PageTransition>
      <div className="p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold font-display text-mitti-900 dark:text-kora-100 mb-2">
              {t('departmentDashboard.title', 'Department Dashboard')} - {department.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </h1>
            <p className="text-mitti-600 dark:text-mitti-400">{t('departmentDashboard.filterByStatus', 'Manage and resolve citizen grievances')}</p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4 mb-6">
            {statCards.map((card, i) => (
              <motion.div
                key={card.label}
                className="village-card rounded-xl p-4"
                custom={i}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 ${card.iconBg} rounded-lg`}>{card.icon}</div>
                  <div>
                    <p className="text-2xl font-bold font-display text-mitti-900 dark:text-kora-100">{card.value}</p>
                    <p className="text-xs text-mitti-500 dark:text-mitti-400">{card.label}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Category Chart */}
          {categoryData.length > 0 && (
            <div className="village-card rounded-xl p-6 mb-6">
              <h2 className="text-lg font-semibold text-mitti-900 dark:text-kora-100 mb-4">Grievances by Category</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={categoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#292524',
                      border: '1px solid rgba(139,90,43,0.3)',
                      borderRadius: '8px',
                      color: '#fff',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                    }}
                  />
                  <Bar dataKey="count" fill="#8B5A2B" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Filters */}
          <div className="mb-6 flex flex-wrap gap-2 village-card p-2 rounded-xl inline-flex">
            {['pending', 'accepted', 'in_progress', 'resolved'].map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  filter === status
                    ? 'bg-mitti-500 text-white shadow-mitti'
                    : 'text-mitti-700 dark:text-mitti-300 hover:bg-mitti-100/50 dark:hover:bg-night-card/50'
                }`}
              >
                {status === 'pending' ? t('common.pending', 'PENDING') :
                 status === 'accepted' ? t('common.accepted', 'ACCEPTED') :
                 status === 'in_progress' ? t('common.inProgress', 'IN PROGRESS') :
                 t('common.resolved', 'RESOLVED')}
              </button>
            ))}
          </div>

          {/* Grievances List */}
          {loading ? (
            <div className="text-center py-12">
              <ThemedSpinner />
              <p className="mt-4 text-mitti-600 dark:text-mitti-400">{t('grievances.processing', 'Loading grievances...')}</p>
            </div>
          ) : grievances.length === 0 ? (
            <div className="village-card rounded-xl p-12 text-center">
              <AlertCircle className="w-16 h-16 text-mitti-400 mx-auto mb-4" />
              <p className="text-mitti-600 dark:text-mitti-400 text-lg">{t('departmentDashboard.noPendingGrievances', `No ${filter.replace('_', ' ')} grievances found`)}</p>
            </div>
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {grievances.map((grievance, index) => (
                  <motion.div
                    key={grievance.grievance_id}
                    className="village-card rounded-xl overflow-hidden hover:shadow-md transition-all"
                    initial="hidden"
                    animate="visible"
                    exit="hidden"
                    variants={grievanceVariants}
                    transition={{ delay: index * 0.05 }}
                  >
                    <div className="p-4 md:p-6">
                      <div className="flex flex-col md:flex-row md:items-start justify-between mb-4 gap-4">
                        <div className="flex-1">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className="font-mono text-sm text-mitti-600 dark:text-mitti-400 font-semibold">{grievance.grievance_id}</span>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold border-2 ${getPriorityColor(grievance.priority)}`}>
                              {grievance.priority?.toUpperCase()}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusBadge(grievance.status)}`}>
                              {grievance.status?.replace('_', ' ').toUpperCase()}
                            </span>
                            <span className="text-sm text-mitti-500 dark:text-mitti-400">
                              <Clock className="w-4 h-4 inline mr-1" />
                              {formatDate(grievance.submitted_at)}
                            </span>
                          </div>

                          <h3 className="text-xl font-bold text-mitti-900 dark:text-kora-100 mb-2">{grievance.title}</h3>
                          <p className="text-mitti-700 dark:text-mitti-300 mb-4">{grievance.description}</p>

                          <div className="flex flex-wrap gap-4 text-sm text-mitti-600 dark:text-mitti-400 mb-4">
                            <div className="flex items-center"><User className="w-4 h-4 mr-1" />{grievance.citizen_name}</div>
                            <div className="flex items-center"><Phone className="w-4 h-4 mr-1" />{grievance.citizen_phone}</div>
                          </div>

                          {grievance.routing_reasoning && (
                            <div className="p-4 bg-mitti-50 dark:bg-mitti-900/20 rounded-lg border border-mitti-200 dark:border-mitti-800">
                              <p className="text-sm font-semibold text-mitti-900 dark:text-mitti-300 mb-1">{t('grievances.aiRouting', 'AI Routing Analysis')}</p>
                              <p className="text-sm text-mitti-800 dark:text-mitti-200">{grievance.routing_reasoning}</p>
                            </div>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="flex flex-row md:flex-col gap-2 flex-wrap md:ml-6">
                          {filter === 'pending' && (
                            <>
                              <button onClick={() => setActionModal({ type: 'accept', grievanceId: grievance.grievance_id })} disabled={actionLoading}
                                className="px-5 py-2.5 bg-india-green-600 text-white rounded-lg hover:bg-india-green-700 font-semibold shadow-lg transition-all disabled:bg-gray-400 flex items-center text-sm">
                                <Check className="w-4 h-4 mr-2" />{t('grievances.accept', 'Accept')}
                              </button>
                              <button onClick={() => setActionModal({ type: 'reject', grievanceId: grievance.grievance_id })} disabled={actionLoading}
                                className="px-5 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 font-semibold shadow-lg transition-all disabled:bg-gray-400 flex items-center text-sm">
                                <X className="w-4 h-4 mr-2" />{t('grievances.reject', 'Reject')}
                              </button>
                            </>
                          )}
                          {filter === 'accepted' && (
                            <>
                              <button onClick={() => handleMarkInProgress(grievance.grievance_id)} disabled={actionLoading}
                                className="px-5 py-2.5 bg-mitti-600 text-white rounded-lg hover:bg-mitti-700 font-semibold shadow-lg transition-all disabled:bg-gray-400 flex items-center text-sm">
                                <PlayCircle className="w-4 h-4 mr-2" />{t('departmentDashboard.startWork', 'Start Work')}
                              </button>
                              <button onClick={() => setActionModal({ type: 'resolve', grievanceId: grievance.grievance_id })} disabled={actionLoading}
                                className="px-5 py-2.5 bg-india-green-600 text-white rounded-lg hover:bg-india-green-700 font-semibold shadow-lg transition-all disabled:bg-gray-400 flex items-center text-sm">
                                <Check className="w-4 h-4 mr-2" />{t('grievances.resolve', 'Resolve')}
                              </button>
                            </>
                          )}
                          {filter === 'in_progress' && (
                            <button onClick={() => setActionModal({ type: 'resolve', grievanceId: grievance.grievance_id })} disabled={actionLoading}
                              className="px-5 py-2.5 bg-india-green-600 text-white rounded-lg hover:bg-india-green-700 font-semibold shadow-lg transition-all disabled:bg-gray-400 flex items-center text-sm">
                              <Check className="w-4 h-4 mr-2" />{t('grievances.resolve', 'Resolve')}
                            </button>
                          )}
                          {/* Expand comments toggle for non-pending */}
                          {filter !== 'pending' && (
                            <button onClick={() => toggleExpand(grievance.grievance_id)}
                              className="px-5 py-2.5 bg-mitti-100 dark:bg-night-card text-mitti-700 dark:text-mitti-300 rounded-lg hover:bg-mitti-200 dark:hover:bg-night-card/80 font-medium transition-all flex items-center text-sm">
                              <MessageSquare className="w-4 h-4 mr-2" />
                              {t('common.comments', 'Comments')}
                              {expandedGrievance === grievance.grievance_id ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-4 border-t border-mitti-200 dark:border-night-border">
                        <div className="flex items-center text-sm text-mitti-600 dark:text-mitti-400">
                          <Clock className="w-4 h-4 mr-2" />
                          Estimated resolution: <span className="font-semibold ml-1">{grievance.estimated_resolution_days} days</span>
                        </div>
                        <div className="text-xs text-mitti-500 uppercase tracking-wider">{grievance.category?.replace('_', ' ')}</div>
                      </div>
                    </div>

                    {/* Expanded Comments Section */}
                    <AnimatePresence>
                      {expandedGrievance === grievance.grievance_id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.3 }}
                          className="overflow-hidden"
                        >
                          <div className="border-t border-mitti-200 dark:border-night-border village-card-subtle p-6">
                            <h4 className="text-sm font-semibold text-mitti-900 dark:text-kora-100 mb-4 flex items-center">
                              <MessageSquare className="w-4 h-4 mr-2" />
                              {t('departmentDashboard.addNote', 'Case Comments & Updates')}
                            </h4>

                            {/* Comments List */}
                            {commentsLoading === grievance.grievance_id ? (
                              <div className="text-center py-4">
                                <ThemedSpinner />
                              </div>
                            ) : (comments[grievance.grievance_id] || []).length === 0 ? (
                              <p className="text-sm text-mitti-500 dark:text-mitti-400 italic mb-4">No comments yet. Add an update below.</p>
                            ) : (
                              <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
                                {(comments[grievance.grievance_id] || []).map((comment) => (
                                  <div key={comment.id} className={`p-3 rounded-lg ${
                                    comment.author_role === 'officer' || comment.author_role === 'admin'
                                      ? 'bg-mitti-50 dark:bg-mitti-900/20 border border-mitti-200 dark:border-mitti-800 ml-4'
                                      : 'village-card border border-mitti-200 dark:border-night-border mr-4'
                                  }`}>
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="text-xs font-semibold text-mitti-900 dark:text-kora-100">
                                        {comment.author_name}
                                        <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] ${
                                          comment.author_role === 'officer' ? 'bg-mitti-100 text-mitti-600 dark:bg-mitti-900/50 dark:text-mitti-400' :
                                          comment.author_role === 'admin' ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400' :
                                          'bg-mitti-100 text-mitti-600 dark:bg-night-card dark:text-mitti-400'
                                        }`}>{comment.author_role}</span>
                                        {!comment.is_public && (
                                          <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-orange-100 text-orange-600 dark:bg-orange-900/50 dark:text-orange-400">Internal</span>
                                        )}
                                      </span>
                                      <span className="text-[10px] text-mitti-400">{formatDate(comment.created_at)}</span>
                                    </div>
                                    <p className="text-sm text-mitti-700 dark:text-mitti-300">{comment.comment_text}</p>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Add Comment (only for accepted/in_progress) */}
                            {(filter === 'accepted' || filter === 'in_progress') && (
                              <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-3">
                                  <label className="flex items-center gap-1.5 text-xs text-mitti-600 dark:text-mitti-400 cursor-pointer">
                                    <input type="checkbox" checked={commentIsPublic} onChange={() => setCommentIsPublic(!commentIsPublic)}
                                      className="rounded border-mitti-300 text-mitti-600 focus:ring-mitti-500" />
                                    Visible to citizen
                                  </label>
                                </div>
                                <div className="flex gap-2">
                                  <input
                                    type="text"
                                    value={newComment}
                                    onChange={(e) => setNewComment(e.target.value)}
                                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendComment(grievance.grievance_id); } }}
                                    placeholder="Add a comment or update..."
                                    className="village-input flex-1 px-3 py-2 rounded-lg text-sm focus:ring-2 focus:ring-mitti-500 focus:border-transparent"
                                  />
                                  <button
                                    onClick={() => handleSendComment(grievance.grievance_id)}
                                    disabled={sendingComment || !newComment.trim()}
                                    className="px-4 py-2 bg-mitti-600 text-white rounded-lg hover:bg-mitti-700 disabled:bg-gray-400 transition-all flex items-center text-sm font-medium"
                                  >
                                    <Send className="w-4 h-4 mr-1" />
                                    {t('common.send', 'Send')}
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* Read-only for resolved */}
                            {filter === 'resolved' && (comments[grievance.grievance_id] || []).length > 0 && (
                              <p className="text-xs text-mitti-400 italic mt-2">This case is resolved. Comments are read-only.</p>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Action Modal */}
        <AnimatePresence>
          {actionModal && (
            <motion.div
              className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="village-card rounded-xl shadow-2xl w-full max-w-md p-6"
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              >
                <h3 className="text-lg font-bold text-mitti-900 dark:text-kora-100 mb-4">
                  {actionModal.type === 'accept' ? t('grievances.accept', 'Accept Grievance') : actionModal.type === 'reject' ? t('grievances.reject', 'Reject Grievance') : t('departmentDashboard.resolveGrievance', 'Resolve Grievance')}
                </h3>
                <div className="space-y-4">
                  <div className="p-3 village-card-subtle rounded-lg">
                    <p className="text-xs text-mitti-500 dark:text-mitti-400 mb-1">Acting as</p>
                    <p className="font-semibold text-mitti-900 dark:text-kora-100">{officerName}</p>
                  </div>

                  {actionModal.type === 'accept' && (
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">Notes (optional)</label>
                      <textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                        className="village-input w-full px-3 py-2 rounded-lg focus:ring-2 focus:ring-mitti-500" rows={3} placeholder="Add notes about acceptance..." />
                    </div>
                  )}

                  {actionModal.type === 'reject' && (
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">Rejection Reason *</label>
                      <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                        className="village-input w-full px-3 py-2 rounded-lg focus:ring-2 focus:ring-mitti-500" rows={3} placeholder="Reason for rejection..." />
                    </div>
                  )}

                  {actionModal.type === 'resolve' && (
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">Resolution Notes *</label>
                      <textarea value={formData.resolution} onChange={(e) => setFormData({ ...formData, resolution: e.target.value })}
                        className="village-input w-full px-3 py-2 rounded-lg focus:ring-2 focus:ring-mitti-500" rows={4} placeholder="Describe how this grievance was resolved, what actions were taken, and the outcome..." />
                    </div>
                  )}
                </div>

                <div className="flex justify-end space-x-3 mt-6">
                  <button onClick={() => { setActionModal(null); setFormData({ notes: '', reason: '', resolution: '' }); }}
                    className="px-4 py-2 border border-mitti-300 dark:border-night-border rounded-lg text-mitti-700 dark:text-mitti-300 hover:bg-mitti-50 dark:hover:bg-night-card">{t('common.cancel', 'Cancel')}</button>
                  <button onClick={actionModal.type === 'accept' ? handleAccept : actionModal.type === 'reject' ? handleReject : handleResolve}
                    disabled={actionLoading || (actionModal.type === 'reject' && !formData.reason) || (actionModal.type === 'resolve' && !formData.resolution)}
                    className={`px-4 py-2 rounded-lg text-white font-medium disabled:bg-gray-400 ${
                      actionModal.type === 'accept' ? 'bg-india-green-600 hover:bg-india-green-700' : actionModal.type === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-india-green-600 hover:bg-india-green-700'
                    }`}>
                    {actionLoading ? t('grievances.processing', 'Processing...') : actionModal.type === 'accept' ? t('grievances.accept', 'Accept') : actionModal.type === 'reject' ? t('grievances.reject', 'Reject') : t('grievances.resolve', 'Resolve')}
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
};

export default DepartmentDashboard;
