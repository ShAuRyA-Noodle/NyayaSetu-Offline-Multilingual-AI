import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Activity, Users, FileText, TrendingUp, ArrowUpRight, Clock, CheckCircle, AlertTriangle, Shield, BarChart3, ArrowRight, Sparkles } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import CountUp from '../components/ui/CountUp';

const stagger = {
  container: {
    initial: {},
    animate: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
  },
  item: {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: {
      opacity: 1, y: 0, scale: 1,
      transition: { duration: 0.5, ease: [0.25, 1, 0.5, 1] as const },
    },
  },
};

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const role = user?.role || 'citizen';

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>({});
  const [grievanceStats, setGrievanceStats] = useState<any>(null);
  const [myGrievances, setMyGrievances] = useState<any[]>([]);
  const [slaData, setSlaData] = useState<any>(null);
  const [trendData, setTrendData] = useState<any[]>([]);

  useEffect(() => { loadDashboardData(); }, [role]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const promises: Promise<any>[] = [apiService.getStats().catch(() => ({}))];
      if (role === 'citizen') {
        promises.push(apiService.getMyGrievances().catch(() => ({ grievances: [] })));
      } else if (role === 'officer') {
        promises.push(apiService.getGrievanceStats().catch(() => ({})));
        promises.push(apiService.slaDashboard().catch(() => ({})));
      } else if (role === 'admin') {
        promises.push(apiService.adminAnalyticsOverview().catch(() => ({})));
        promises.push(apiService.adminAnalyticsTrends(7).catch(() => ({ trends: [] })));
        promises.push(apiService.slaDashboard().catch(() => ({})));
      }
      const results = await Promise.all(promises);
      setStats(results[0] || {});
      if (role === 'citizen') setMyGrievances((results[1]?.grievances || []).slice(0, 5));
      else if (role === 'officer') { setGrievanceStats(results[1] || {}); setSlaData(results[2] || {}); }
      else if (role === 'admin') { setGrievanceStats(results[1] || {}); setTrendData(results[2]?.trends || []); setSlaData(results[3] || {}); }
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  // ─── Stat Card ───
  const StatCard = ({ icon: Icon, title, value, accent = 'mitti', onClick }: any) => {
    const accentColors: any = {
      mitti: 'from-[#0D92F4] to-[#0D92F4]/80',
      haldi: 'from-[#77CDFF] to-[#0D92F4]',
      neel: 'from-neel-500 to-neel-600',
      green: 'from-india-green-500 to-india-green-600',
    };
    const glowColors: any = {
      mitti: 'rgba(13,146,244,0.15)',
      haldi: 'rgba(119,205,255,0.12)',
      neel: 'rgba(45,74,122,0.12)',
      green: 'rgba(19,136,8,0.12)',
    };
    return (
      <motion.div
        variants={stagger.item}
        onClick={onClick}
        className={`village-card p-5 ${onClick ? 'cursor-pointer' : ''} group`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${accentColors[accent]} flex items-center justify-center shadow-lg`}
            style={{ boxShadow: `0 4px 20px ${glowColors[accent]}` }}>
            <Icon className="w-5 h-5 text-white" strokeWidth={1.8} />
          </div>
          {onClick && <ArrowUpRight className="w-4 h-4 text-slate-500/30 group-hover:text-[#77CDFF] transition-colors" />}
        </div>
        <p className="text-xs text-slate-400/50 mb-1 uppercase tracking-wider font-medium">{title}</p>
        <p className="text-3xl font-display font-bold text-kora-100">
          {typeof value === 'number' ? <CountUp end={value} duration={1200} /> : value ?? 0}
        </p>
      </motion.div>
    );
  };

  const getStatusBadge = (status: string) => {
    const styles: any = {
      resolved: 'bg-india-green-500/10 text-india-green-400 border-india-green-500/20',
      pending: 'bg-haldi-500/10 text-haldi-400 border-haldi-500/20',
      accepted: 'bg-[#0D92F4]/10 text-[#77CDFF] border-[#0D92F4]/20',
      'in-progress': 'bg-neel-500/10 text-neel-400 border-neel-500/20',
    };
    return `px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${styles[status] || styles.pending}`;
  };

  const chartTooltipStyle = {
    backgroundColor: 'rgba(8, 16, 32, 0.92)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(119, 205, 255, 0.08)',
    borderRadius: '10px',
    color: '#E2E8F0',
    fontSize: '12px',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <ThemedSpinner size="lg" />
          <p className="mt-4 text-slate-400/40 text-sm">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  // ─── Greeting based on time ───
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

  return (
    <PageTransition>
      <div className="p-4 md:p-6 lg:p-8 space-y-6 min-h-screen">

        {/* ─── Hero Header ─── */}
        <motion.div
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div>
            <h1 className="text-2xl md:text-3xl font-display font-bold text-kora-100 tracking-tight">
              {greeting}, <span className="text-gradient-gold">{user?.username || 'User'}</span>
            </h1>
            <p className="text-sm text-slate-400/40 mt-1">
              {t('dashboard.welcomeBack')} · <span className="capitalize">{role}</span> Dashboard
            </p>
          </div>
          <motion.button
            onClick={loadDashboardData}
            className="btn-glass text-xs py-2 px-4"
            whileTap={{ scale: 0.97 }}
          >
            {t('common.refresh')}
          </motion.button>
        </motion.div>

        {/* ═══ CITIZEN DASHBOARD ═══ */}
        {role === 'citizen' && (
          <>
            {/* Stats grid */}
            <motion.div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4"
              variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={Activity} title={t('dashboard.totalQueries')} value={stats.total_requests || 0} accent="mitti" />
              <StatCard icon={FileText} title={t('dashboard.myGrievances')} value={myGrievances.length} accent="haldi" onClick={() => navigate('/grievances')} />
              <StatCard icon={Users} title={t('dashboard.schemesAvailable')} value={stats.schemes_indexed || 0} accent="neel" onClick={() => navigate('/schemes')} />
              <StatCard icon={TrendingUp} title={t('dashboard.successRate')} value={`${stats.success_rate || 0}%`} accent="green" />
            </motion.div>

            {/* Two column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              {/* Recent grievances */}
              <motion.div className="lg:col-span-3 village-card p-5"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-kora-200 uppercase tracking-wider">{t('dashboard.recentGrievances')}</h2>
                  <button onClick={() => navigate('/grievances')} className="text-xs text-slate-400/50 hover:text-[#77CDFF] font-medium transition-colors flex items-center gap-1">
                    {t('common.viewAll')} <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                {myGrievances.length === 0 ? (
                  <div className="text-center py-10">
                    <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center mx-auto mb-3">
                      <FileText className="w-5 h-5 text-[#0D92F4]/20" />
                    </div>
                    <p className="text-sm text-slate-500/30">{t('dashboard.noGrievances')}</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {myGrievances.map((g: any, i: number) => (
                      <motion.div key={g.grievance_id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.35 + i * 0.05 }}
                        className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.08] transition-colors"
                      >
                        <div className="flex-1 min-w-0 mr-3">
                          <p className="text-sm font-medium text-kora-200 truncate">{g.title || g.description?.slice(0, 60)}</p>
                          <p className="text-[11px] text-slate-500/30 mt-0.5">{g.grievance_id} · {new Date(g.submitted_at).toLocaleDateString()}</p>
                        </div>
                        <span className={getStatusBadge(g.status)}>{g.status?.toUpperCase()}</span>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>

              {/* Quick actions */}
              <motion.div className="lg:col-span-2 space-y-3"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                <h2 className="text-sm font-semibold text-kora-200 uppercase tracking-wider px-1">{t('dashboard.howCanWeHelp')}</h2>
                {[
                  { path: '/schemes', label: t('dashboard.viewSchemes'), desc: t('dashboard.browseSchemes'), icon: FileText },
                  { path: '/chat', label: t('dashboard.askQuestion'), desc: t('dashboard.getAnswers'), icon: Sparkles },
                  { path: '/grievances', label: t('dashboard.submitGrievance'), desc: t('dashboard.fileGrievance'), icon: AlertTriangle },
                ].map((action) => (
                  <motion.button
                    key={action.path}
                    onClick={() => navigate(action.path)}
                    className="w-full village-card p-4 text-left group flex items-center gap-4"
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0 group-hover:border-[#0D92F4]/20 transition-colors">
                      <action.icon className="w-5 h-5 text-slate-400/50 group-hover:text-[#77CDFF] transition-colors" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-kora-200 group-hover:text-kora-100 transition-colors">{action.label}</p>
                      <p className="text-[11px] text-slate-400/35 mt-0.5">{action.desc}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#0D92F4]/20 group-hover:text-[#77CDFF] transition-all group-hover:translate-x-1" />
                  </motion.button>
                ))}
              </motion.div>
            </div>
          </>
        )}

        {/* ═══ OFFICER DASHBOARD ═══ */}
        {role === 'officer' && (
          <>
            <motion.div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4"
              variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={AlertTriangle} title={t('dashboard.pendingReview')} value={grievanceStats?.pending_grievances || stats.pending_grievances || 0} accent="mitti" onClick={() => navigate('/department')} />
              <StatCard icon={CheckCircle} title={t('dashboard.resolvedToday')} value={grievanceStats?.resolved_grievances || 0} accent="green" />
              <StatCard icon={Clock} title={t('dashboard.slaCompliance')} value={`${slaData?.overall_compliance || 0}%`} accent="neel" />
              <StatCard icon={FileText} title={t('dashboard.schemesAvailable')} value={stats.schemes_indexed || 0} accent="haldi" onClick={() => navigate('/schemes')} />
            </motion.div>

            {slaData?.departments && (
              <motion.div className="village-card p-5" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <h2 className="text-sm font-semibold text-kora-200 uppercase tracking-wider mb-4">{t('dashboard.departmentOverview')}</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={slaData.departments.slice(0, 8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="department" stroke="rgba(13,146,244,0.3)" tick={{ fontSize: 11, fill: 'rgba(13,146,244,0.4)' }} />
                    <YAxis stroke="rgba(13,146,244,0.3)" tick={{ fill: 'rgba(13,146,244,0.4)' }} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Bar dataKey="compliance_rate" fill="rgba(13,146,244,0.6)" radius={[6, 6, 0, 0]} name="Compliance %" />
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            {/* Quick actions */}
            <motion.div className="grid grid-cols-1 sm:grid-cols-3 gap-3"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              {[
                { path: '/department', label: 'Department Queue', accent: 'text-[#77CDFF]' },
                { path: '/notices', label: 'Draft Notice', accent: 'text-neel-400' },
                { path: '/grievances', label: 'Assigned Cases', accent: 'text-haldi-400' },
              ].map((a) => (
                <motion.button key={a.path} onClick={() => navigate(a.path)}
                  className="village-card p-4 text-sm font-semibold text-center hover:border-[#0D92F4]/15 transition-colors"
                  whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                  <span className={a.accent}>{a.label}</span>
                </motion.button>
              ))}
            </motion.div>
          </>
        )}

        {/* ═══ ADMIN DASHBOARD ═══ */}
        {role === 'admin' && (
          <>
            <motion.div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4"
              variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={Users} title={t('dashboard.totalUsers')} value={grievanceStats?.total_users || 0} accent="mitti" onClick={() => navigate('/admin')} />
              <StatCard icon={AlertTriangle} title={t('dashboard.activeGrievances')} value={grievanceStats?.active_grievances || stats.pending_grievances || 0} accent="haldi" />
              <StatCard icon={Shield} title={t('dashboard.slaCompliance')} value={`${slaData?.overall_compliance || 0}%`} accent="neel" />
              <StatCard icon={BarChart3} title={t('dashboard.avgResolution')} value={grievanceStats?.avg_satisfaction ? `${grievanceStats.avg_satisfaction.toFixed(1)}/5` : 'N/A'} accent="green" />
            </motion.div>

            {trendData.length > 0 && (
              <motion.div className="village-card p-5" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <h2 className="text-sm font-semibold text-kora-200 uppercase tracking-wider mb-4">{t('dashboard.recentActivity')}</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="colorG" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C27B3A" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#C27B3A" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="date" stroke="rgba(13,146,244,0.3)" tick={{ fontSize: 11, fill: 'rgba(13,146,244,0.4)' }} />
                    <YAxis stroke="rgba(13,146,244,0.3)" tick={{ fill: 'rgba(13,146,244,0.4)' }} />
                    <Tooltip contentStyle={chartTooltipStyle} />
                    <Area type="monotone" dataKey="grievances" stroke="#C27B3A" strokeWidth={2} fill="url(#colorG)" />
                    <Area type="monotone" dataKey="queries" stroke="rgba(45,74,122,0.5)" strokeWidth={1.5} fillOpacity={0} />
                  </AreaChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            <motion.div className="grid grid-cols-2 sm:grid-cols-4 gap-3"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              {[
                { path: '/admin', label: 'Admin Panel', accent: 'text-[#77CDFF]' },
                { path: '/department', label: 'Departments', accent: 'text-neel-400' },
                { path: '/schemes', label: 'Manage Schemes', accent: 'text-haldi-400' },
                { path: '/notices', label: 'Notices', accent: 'text-india-green-400' },
              ].map((a) => (
                <motion.button key={a.path} onClick={() => navigate(a.path)}
                  className="village-card p-4 text-sm font-semibold text-center hover:border-[#0D92F4]/15 transition-colors"
                  whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                  <span className={a.accent}>{a.label}</span>
                </motion.button>
              ))}
            </motion.div>
          </>
        )}
      </div>
    </PageTransition>
  );
};

export default Dashboard;
