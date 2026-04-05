import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Activity, Users, FileText, TrendingUp, ArrowUpRight, Clock, CheckCircle, AlertTriangle, Shield, BarChart3 } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import TextReveal from '../components/ui/TextReveal';
import WarliIllustration from '../components/decorative/WarliIllustration';
import { useTilt } from '../hooks/useTilt';

const stagger = {
  container: { animate: { transition: { staggerChildren: 0.08 } } },
  item: { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 } },
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

  const iconBgs = ['bg-mitti-500', 'bg-haldi-500', 'bg-neel-500', 'bg-india-green-500'];

  const StatCard = ({ icon: Icon, title, value, colorIdx = 0, onClick }: any) => {
    const tiltRef = useTilt<HTMLDivElement>(6);
    return (
      <motion.div
        ref={tiltRef}
        variants={stagger.item}
        onClick={onClick}
        className={`village-card p-5 md:p-6 hover:shadow-mitti-lg transition-all duration-300 ${onClick ? 'cursor-pointer' : ''} group`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl ${iconBgs[colorIdx % 4]} group-hover:scale-110 transition-transform duration-300 shadow-lg grain-overlay`}>
            <Icon className="w-6 h-6 text-white relative z-10" />
          </div>
          {onClick && <ArrowUpRight className="w-4 h-4 text-mitti-400 group-hover:text-mitti-500 transition-colors" />}
        </div>
        <p className="text-sm text-mitti-600 dark:text-mitti-400 mb-1">{title}</p>
        <p className="text-3xl md:text-4xl font-display font-bold text-mitti-900 dark:text-kora-100">{value ?? 0}</p>
      </motion.div>
    );
  };

  const getStatusBadge = (status: string) => {
    const cls = status === 'resolved' ? 'badge-resolved' : status === 'pending' ? 'badge-pending' : 'badge-accepted';
    return `px-2.5 py-1 rounded-full text-xs font-bold ${cls}`;
  };

  const tooltipStyle = {
    backgroundColor: 'rgba(251, 247, 240, 0.95)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(194, 123, 58, 0.2)',
    borderRadius: '12px',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <ThemedSpinner size="lg" />
          <p className="mt-4 text-mitti-500 dark:text-mitti-400 font-medium">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="p-4 md:p-6 lg:p-10 space-y-8 min-h-screen">
        {/* Hero Header */}
        <motion.div
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-start gap-4">
            <div className="hidden md:block opacity-15 mt-2">
              <WarliIllustration variant="village" size={100} />
            </div>
            <div>
              <TextReveal as="h1" className="text-3xl md:text-hero-sm font-display font-bold text-mitti-900 dark:text-kora-100" splitBy="word" stagger={0.03}>
                {t('dashboard.title')}
              </TextReveal>
              <p className="text-mitti-600 dark:text-mitti-400 mt-1">
                {t('dashboard.welcomeBack')}, <span className="text-mitti-500 font-semibold">{user?.username || 'User'}</span>
              </p>
              <p className="font-devanagari text-lg text-mitti-400 dark:text-mitti-500 mt-0.5">स्वागत है</p>
            </div>
          </div>
          <motion.button
            onClick={loadDashboardData}
            className="btn-mitti text-sm py-2 px-4"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            {t('common.refresh')}
          </motion.button>
        </motion.div>

        {/* === CITIZEN DASHBOARD === */}
        {role === 'citizen' && (
          <>
            <motion.div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6" variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={Activity} title={t('dashboard.totalQueries')} value={stats.total_requests || 0} colorIdx={0} />
              <StatCard icon={FileText} title={t('dashboard.myGrievances')} value={myGrievances.length} colorIdx={1} onClick={() => navigate('/grievances')} />
              <StatCard icon={Users} title={t('dashboard.schemesAvailable')} value={stats.schemes_indexed || 0} colorIdx={2} onClick={() => navigate('/schemes')} />
              <StatCard icon={TrendingUp} title={t('dashboard.successRate')} value={`${stats.success_rate || 0}%`} colorIdx={3} />
            </motion.div>

            {/* Recent Grievances */}
            <motion.div className="village-card p-5 md:p-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-display font-semibold text-mitti-900 dark:text-kora-100">{t('dashboard.recentGrievances')}</h2>
                <button onClick={() => navigate('/grievances')} className="text-sm text-mitti-500 hover:text-mitti-600 font-medium">{t('common.viewAll')}</button>
              </div>
              {myGrievances.length === 0 ? (
                <div className="text-center py-8">
                  <div className="opacity-10 mb-4"><WarliIllustration variant="panchayat" size={120} className="mx-auto" /></div>
                  <p className="text-mitti-400 dark:text-night-muted">{t('dashboard.noGrievances')}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {myGrievances.map((g: any) => (
                    <div key={g.grievance_id} className="flex items-center justify-between p-3 village-card-subtle rounded-xl">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-mitti-900 dark:text-kora-200 truncate">{g.title || g.description?.slice(0, 60)}</p>
                        <p className="text-xs text-mitti-400 dark:text-night-muted">{g.grievance_id} &middot; {new Date(g.submitted_at).toLocaleDateString()}</p>
                      </div>
                      <span className={getStatusBadge(g.status)}>{g.status?.toUpperCase()}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Quick Actions — Full bleed mitti */}
            <motion.div
              className="bg-gradient-mitti rounded-2xl shadow-mitti-lg p-5 md:p-8 text-white relative overflow-hidden"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="absolute top-4 right-4 opacity-10">
                <WarliIllustration variant="tree" size={120} color="#fff" />
              </div>
              <h2 className="text-2xl font-display font-bold mb-2 relative z-10">{t('dashboard.howCanWeHelp')}</h2>
              <p className="text-mitti-100/80 mb-6 relative z-10">{t('dashboard.accessFeatures')}</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 relative z-10">
                {[
                  { path: '/schemes', label: t('dashboard.viewSchemes'), desc: t('dashboard.browseSchemes') },
                  { path: '/chat', label: t('dashboard.askQuestion'), desc: t('dashboard.getAnswers') },
                  { path: '/grievances', label: t('dashboard.submitGrievance'), desc: t('dashboard.fileGrievance') },
                ].map((action) => (
                  <motion.button
                    key={action.path}
                    onClick={() => navigate(action.path)}
                    className="p-4 bg-white/90 dark:bg-night-card/80 text-left rounded-xl hover:bg-white transition-all shadow-md group"
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <p className="font-semibold text-mitti-800 dark:text-kora-100 group-hover:text-mitti-500">{action.label}</p>
                    <p className="text-xs text-mitti-600 dark:text-mitti-400 mt-1">{action.desc}</p>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </>
        )}

        {/* === OFFICER DASHBOARD === */}
        {role === 'officer' && (
          <>
            <motion.div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6" variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={AlertTriangle} title={t('dashboard.pendingReview')} value={grievanceStats?.pending_grievances || stats.pending_grievances || 0} colorIdx={0} onClick={() => navigate('/department')} />
              <StatCard icon={CheckCircle} title={t('dashboard.resolvedToday')} value={grievanceStats?.resolved_grievances || 0} colorIdx={1} />
              <StatCard icon={Clock} title={t('dashboard.slaCompliance')} value={`${slaData?.overall_compliance || 0}%`} colorIdx={2} />
              <StatCard icon={FileText} title={t('dashboard.schemesAvailable')} value={stats.schemes_indexed || 0} colorIdx={3} onClick={() => navigate('/schemes')} />
            </motion.div>

            {slaData?.departments && (
              <motion.div className="village-card p-5 md:p-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <h2 className="text-lg font-display font-semibold text-mitti-900 dark:text-kora-100 mb-4">{t('dashboard.departmentOverview')}</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={slaData.departments.slice(0, 8)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(194,123,58,0.1)" />
                    <XAxis dataKey="department" stroke="#A66228" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#A66228" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="compliance_rate" fill="#C27B3A" radius={[8, 8, 0, 0]} name="Compliance %" />
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            <motion.div
              className="bg-gradient-mitti rounded-2xl shadow-mitti-lg p-6 text-white relative overflow-hidden"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            >
              <h2 className="text-xl font-display font-bold mb-4">{t('dashboard.quickActions')}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <motion.button onClick={() => navigate('/department')} className="p-4 bg-white/90 text-mitti-700 rounded-xl font-medium shadow-md hover:bg-white transition-all" whileHover={{ y: -2 }}>Department Queue</motion.button>
                <motion.button onClick={() => navigate('/notices')} className="p-4 bg-white/90 text-neel-600 rounded-xl font-medium shadow-md hover:bg-white transition-all" whileHover={{ y: -2 }}>Draft Notice</motion.button>
                <motion.button onClick={() => navigate('/grievances')} className="p-4 bg-white/90 text-haldi-600 rounded-xl font-medium shadow-md hover:bg-white transition-all" whileHover={{ y: -2 }}>Assigned Cases</motion.button>
              </div>
            </motion.div>
          </>
        )}

        {/* === ADMIN DASHBOARD === */}
        {role === 'admin' && (
          <>
            <motion.div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6" variants={stagger.container} initial="initial" animate="animate">
              <StatCard icon={Users} title={t('dashboard.totalUsers')} value={grievanceStats?.total_users || 0} colorIdx={0} onClick={() => navigate('/admin')} />
              <StatCard icon={AlertTriangle} title={t('dashboard.activeGrievances')} value={grievanceStats?.active_grievances || stats.pending_grievances || 0} colorIdx={1} />
              <StatCard icon={Shield} title={t('dashboard.slaCompliance')} value={`${slaData?.overall_compliance || 0}%`} colorIdx={2} />
              <StatCard icon={BarChart3} title={t('dashboard.avgResolution')} value={grievanceStats?.avg_satisfaction ? `${grievanceStats.avg_satisfaction.toFixed(1)}/5` : 'N/A'} colorIdx={3} />
            </motion.div>

            {trendData.length > 0 && (
              <motion.div className="village-card p-5 md:p-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <h2 className="text-lg font-display font-semibold text-mitti-900 dark:text-kora-100 mb-4">{t('dashboard.recentActivity')}</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="colorG" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C27B3A" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#C27B3A" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(194,123,58,0.1)" />
                    <XAxis dataKey="date" stroke="#A66228" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#A66228" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="grievances" stroke="#C27B3A" strokeWidth={2} fill="url(#colorG)" />
                    <Area type="monotone" dataKey="queries" stroke="#2D4A7A" strokeWidth={2} fillOpacity={0} />
                  </AreaChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            <motion.div
              className="bg-gradient-mitti rounded-2xl shadow-mitti-lg p-6 text-white"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            >
              <h2 className="text-xl font-display font-bold mb-4">{t('dashboard.quickActions')}</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4">
                <motion.button onClick={() => navigate('/admin')} className="p-3 md:p-4 bg-white/90 text-mitti-700 rounded-xl font-medium shadow-md hover:bg-white transition-all text-sm" whileHover={{ y: -2 }}>Admin Panel</motion.button>
                <motion.button onClick={() => navigate('/department')} className="p-3 md:p-4 bg-white/90 text-neel-600 rounded-xl font-medium shadow-md hover:bg-white transition-all text-sm" whileHover={{ y: -2 }}>Departments</motion.button>
                <motion.button onClick={() => navigate('/schemes')} className="p-3 md:p-4 bg-white/90 text-haldi-600 rounded-xl font-medium shadow-md hover:bg-white transition-all text-sm" whileHover={{ y: -2 }}>Manage Schemes</motion.button>
                <motion.button onClick={() => navigate('/notices')} className="p-3 md:p-4 bg-white/90 text-mitti-500 rounded-xl font-medium shadow-md hover:bg-white transition-all text-sm" whileHover={{ y: -2 }}>Notices</motion.button>
              </div>
            </motion.div>
          </>
        )}
      </div>
    </PageTransition>
  );
};

export default Dashboard;
