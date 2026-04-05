import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { Users, Shield, AlertTriangle, TrendingUp, Clock, CheckCircle, XCircle, Search, ChevronDown, ChevronUp, Lock, Unlock, BarChart3, KeyRound, Copy, Plus } from 'lucide-react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import apiService from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';

const AdminDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { id: 'overview', label: t('admin.overviewTab', 'Overview') },
    { id: 'grievances', label: t('admin.grievancesTab', 'Grievances') },
    { id: 'users', label: t('admin.usersTab', 'Users') },
    { id: 'officer-codes', label: t('admin.officerCodesTab', 'Officer Codes') },
    { id: 'audit', label: t('admin.auditLogsTab', 'Audit Logs') },
    { id: 'sla', label: t('admin.slaConfigTab', 'SLA Config') },
    { id: 'system', label: t('admin.systemHealthTab', 'System') },
  ];

  return (
    <PageTransition>
      <div className="p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-3xl font-bold font-display text-mitti-900 dark:text-kora-100 mb-2">{t('admin.title', 'Admin Dashboard')}</h1>
            <p className="text-mitti-600 dark:text-mitti-400">System administration and monitoring</p>
          </div>

          <div className="flex space-x-2 mb-6 village-card p-2 rounded-xl inline-flex flex-wrap">
            {tabs.map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 sm:px-5 sm:py-2 rounded-lg font-medium transition-all ${activeTab === tab.id ? 'bg-mitti-500 text-white shadow-mitti' : 'text-mitti-700 dark:text-mitti-300 hover:bg-mitti-100/50 dark:hover:bg-night-card/50'}`}>
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'grievances' && <GrievancesTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'officer-codes' && <OfficerCodesTab />}
          {activeTab === 'audit' && <AuditTab />}
          {activeTab === 'sla' && <SlaConfigTab />}
          {activeTab === 'system' && <SystemTab />}
        </div>
      </div>
    </PageTransition>
  );
};

/* ===================== OVERVIEW TAB ===================== */
const OverviewTab: React.FC = () => {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<any>({});
  const [trends, setTrends] = useState<any[]>([]);
  const [officers, setOfficers] = useState<any[]>([]);
  const [sla, setSla] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [ov, tr, of, sl] = await Promise.all([
        apiService.adminAnalyticsOverview().catch(() => ({})),
        apiService.adminAnalyticsTrends(14).catch(() => ({ trends: [] })),
        apiService.officerPerformance().catch(() => ({ officers: [] })),
        apiService.slaDashboard().catch(() => null),
      ]);
      setOverview(ov);
      // Backend returns grievance_trend/user_trend arrays, merge them by date
      const gTrend = tr.grievance_trend || tr.trends || [];
      const uTrend = tr.user_trend || [];
      const dateMap: Record<string, any> = {};
      gTrend.forEach((d: any) => { dateMap[d.date] = { date: d.date, grievances: d.grievances || d.count || 0 }; });
      uTrend.forEach((d: any) => { if (!dateMap[d.date]) dateMap[d.date] = { date: d.date, grievances: 0 }; dateMap[d.date].users = d.users || d.count || 0; });
      setTrends(Object.values(dateMap).sort((a: any, b: any) => a.date.localeCompare(b.date)));
      // Officer data: normalize field names
      const rawOfficers = of.officers || [];
      setOfficers(rawOfficers.map((o: any) => ({
        ...o,
        username: o.username || o.officer || o.officer_name,
        resolved_count: o.resolved_count ?? o.resolved ?? 0,
        avg_rating: o.avg_rating,
        sla_compliance: o.sla_compliance ?? 0,
      })));
      setSla(sl);
    } catch (err) { console.warn('Failed to load data:', err); } finally { setLoading(false); }
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner /></div>;

  const kpiCards = [
    { icon: Users, label: t('admin.totalUsers', 'Total Users'), value: overview.total_users || 0, color: 'bg-mitti-500' },
    { icon: AlertTriangle, label: 'Active Grievances', value: overview.active_grievances || 0, color: 'bg-haldi-500' },
    { icon: Shield, label: 'SLA Compliance', value: `${sla?.overall_compliance || 0}%`, color: 'bg-neel-500' },
    { icon: TrendingUp, label: 'Avg Satisfaction', value: overview.avg_satisfaction ? `${Number(overview.avg_satisfaction).toFixed(1)}/5` : 'N/A', color: 'bg-terracotta-500' },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((card, index) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.4 }}
          >
            <KpiCard icon={card.icon} label={card.label} value={card.value} color={card.color} />
          </motion.div>
        ))}
      </div>

      {/* Trends Chart */}
      {trends.length > 0 && (
        <div className="village-card rounded-xl p-6">
          <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4">14-Day Trends</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 11 }} />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: 'rgba(251, 247, 240, 0.95)', backdropFilter: 'blur(10px)', border: '1px solid rgba(194, 123, 58, 0.2)', borderRadius: '12px' }} />
              <Line type="monotone" dataKey="grievances" stroke="#C27B3A" strokeWidth={2} dot={false} name="Grievances" />
              <Line type="monotone" dataKey="users" stroke="#2D4A7A" strokeWidth={2} dot={false} name="New Users" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Officer Performance */}
      {officers.length > 0 && (
        <div className="village-card rounded-xl p-6">
          <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4">Officer Performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-mitti-500 dark:text-mitti-400 bg-mitti-50/50 dark:bg-mitti-900/10 border-b border-mitti-200 dark:border-night-border">
                  <th className="pb-3 px-3 font-medium">Officer</th>
                  <th className="pb-3 px-3 font-medium">Resolved</th>
                  <th className="pb-3 px-3 font-medium">Avg Rating</th>
                  <th className="pb-3 px-3 font-medium">SLA Compliance</th>
                </tr>
              </thead>
              <tbody>
                {officers.map((o: any, i: number) => (
                  <tr key={i} className="border-b border-mitti-100 dark:border-night-border/50">
                    <td className="py-3 px-3 font-medium text-mitti-900 dark:text-kora-100">{o.username || o.officer_name || `Officer ${i + 1}`}</td>
                    <td className="py-3 px-3 text-mitti-700 dark:text-mitti-300">{o.resolved_count || 0}</td>
                    <td className="py-3 px-3 text-mitti-700 dark:text-mitti-300">{o.avg_rating ? Number(o.avg_rating).toFixed(1) : 'N/A'}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${(o.sla_compliance || 0) >= 80 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {o.sla_compliance || 0}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const KpiCard = ({ icon: Icon, label, value, color }: { icon: any; label: string; value: any; color: string }) => (
  <div className="village-card rounded-xl p-5">
    <div className="flex items-center space-x-3">
      <div className={`p-3 rounded-lg ${color}`}><Icon className="w-6 h-6 text-white" /></div>
      <div>
        <p className="text-xl md:text-2xl font-bold text-mitti-900 dark:text-kora-100">{value}</p>
        <p className="text-sm text-mitti-500 dark:text-mitti-400">{label}</p>
      </div>
    </div>
  </div>
);

/* ===================== GRIEVANCES TAB ===================== */
const DEPT_OPTIONS = [
  '', 'agriculture', 'education', 'health', 'finance', 'rural_development',
  'urban_development', 'water_resources', 'social_welfare', 'labour',
  'revenue', 'home', 'public_works', 'transport', 'general',
];

const STATUS_OPTIONS = ['', 'pending', 'accepted', 'in_progress', 'resolved', 'rejected'];

const GrievancesTab: React.FC = () => {
  const { t } = useTranslation();
  const [grievances, setGrievances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => { loadGrievances(); }, [statusFilter, deptFilter]);

  const loadGrievances = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAllGrievances(
        statusFilter || undefined,
        deptFilter || undefined,
      );
      setGrievances(data.grievances || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const filtered = grievances.filter(g =>
    !search || g.title?.toLowerCase().includes(search.toLowerCase()) ||
    g.citizen_name?.toLowerCase().includes(search.toLowerCase()) ||
    g.grievance_id?.toLowerCase().includes(search.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-haldi-100 text-haldi-700 dark:bg-haldi-900/30 dark:text-haldi-400',
      accepted: 'bg-mitti-100 text-mitti-700 dark:bg-mitti-900/30 dark:text-mitti-400',
      in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      resolved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    };
    return map[status] || 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
  };

  const getPriorityBadge = (priority: string) => {
    const map: Record<string, string> = {
      critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
      low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    };
    return map[priority] || 'bg-mitti-100 text-mitti-700';
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-mitti-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, citizen, or ID..."
            className="w-full pl-10 pr-4 py-2 village-input rounded-lg text-sm" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 village-input rounded-lg text-sm">
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s ? s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'All Statuses'}</option>
          ))}
        </select>
        <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}
          className="px-3 py-2 village-input rounded-lg text-sm">
          {DEPT_OPTIONS.map(d => (
            <option key={d} value={d}>{d ? d.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'All Departments'}</option>
          ))}
        </select>
      </div>

      {/* Count badge */}
      <p className="text-sm text-mitti-500 dark:text-mitti-400">{filtered.length} grievance{filtered.length !== 1 ? 's' : ''} found</p>

      {loading ? (
        <div className="text-center py-12"><ThemedSpinner /></div>
      ) : filtered.length === 0 ? (
        <div className="village-card rounded-xl p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
          <p className="text-mitti-600 dark:text-mitti-400">{t('admin.noGrievances', 'No grievances match the selected filters.')}</p>
        </div>
      ) : (
        <div className="village-card rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-mitti-500 dark:text-mitti-400 bg-mitti-50/50 dark:bg-mitti-900/10">
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Citizen</th>
                  <th className="px-4 py-3 font-medium">Department</th>
                  <th className="px-4 py-3 font-medium">Priority</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Officer</th>
                  <th className="px-4 py-3 font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((g: any) => (
                  <tr key={g.grievance_id} className="border-t border-mitti-100 dark:border-night-border/50 hover:bg-mitti-50/30 dark:hover:bg-mitti-900/5">
                    <td className="px-4 py-3 font-mono text-xs text-mitti-500 dark:text-mitti-400">{g.grievance_id?.slice(0, 8)}</td>
                    <td className="px-4 py-3 font-medium text-mitti-900 dark:text-kora-100 max-w-[200px] truncate">{g.title}</td>
                    <td className="px-4 py-3 text-mitti-600 dark:text-mitti-300">{g.citizen_name || '-'}</td>
                    <td className="px-4 py-3 text-mitti-600 dark:text-mitti-300 capitalize">{g.department?.replace('_', ' ') || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getPriorityBadge(g.priority)}`}>
                        {g.priority?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusBadge(g.status)}`}>
                        {g.status?.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-mitti-600 dark:text-mitti-300">{g.assigned_officer_name || '-'}</td>
                    <td className="px-4 py-3 text-mitti-500 dark:text-mitti-400 text-xs whitespace-nowrap">
                      {g.submitted_at ? new Date(g.submitted_at).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

/* ===================== USERS TAB ===================== */
const UsersTab: React.FC = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState('');
  const [search, setSearch] = useState('');
  const [editUser, setEditUser] = useState<any>(null);
  const [editRole, setEditRole] = useState('');

  useEffect(() => { loadUsers(); }, [roleFilter]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await apiService.listUsers(roleFilter || undefined);
      setUsers(data.users || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const handleDisable = async (userId: number) => {
    if (!confirm('Disable this user?')) return;
    try { await apiService.disableUser(userId); loadUsers(); } catch { toast.error('Action failed'); }
  };

  const handleUnlock = async (userId: number) => {
    try { await apiService.unlockUser(userId); loadUsers(); } catch { toast.error('Action failed'); }
  };

  const handleUpdateRole = async () => {
    if (!editUser || !editRole) return;
    try {
      await apiService.updateUser(editUser.id, { role: editRole });
      setEditUser(null);
      loadUsers();
    } catch { toast.error('Failed to update'); }
  };

  const filtered = users.filter(u => !search || u.username?.toLowerCase().includes(search.toLowerCase()) || u.email?.toLowerCase().includes(search.toLowerCase()));

  if (loading) return <div className="text-center py-12"><ThemedSpinner /></div>;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-mitti-400" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('admin.searchUsers', 'Search users...')}
            className="w-full pl-10 pr-4 py-2 village-input rounded-lg text-sm" />
        </div>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-2 village-input rounded-lg text-sm">
          <option value="">All Roles</option>
          <option value="citizen">Citizen</option>
          <option value="officer">Officer</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="village-card rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-mitti-500 dark:text-mitti-400 bg-mitti-50/50 dark:bg-mitti-900/10">
                <th className="px-4 py-3 font-medium">{t('admin.username', 'User')}</th>
                <th className="px-4 py-3 font-medium">{t('admin.email', 'Email')}</th>
                <th className="px-4 py-3 font-medium">{t('admin.role', 'Role')}</th>
                <th className="px-4 py-3 font-medium">{t('common.status', 'Status')}</th>
                <th className="px-4 py-3 font-medium">{t('admin.joined', 'Joined')}</th>
                <th className="px-4 py-3 font-medium">{t('common.actions', 'Actions')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u: any) => (
                <tr key={u.id} className="border-t border-mitti-100 dark:border-night-border/50 hover:bg-mitti-50/30 dark:hover:bg-mitti-900/5">
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-8 h-8 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        {u.username?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <span className="font-medium text-mitti-900 dark:text-kora-100">{u.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-mitti-600 dark:text-mitti-300">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      u.role === 'admin' ? 'bg-mitti-100 text-mitti-700 dark:bg-mitti-900/30 dark:text-mitti-400' :
                      u.role === 'officer' ? 'bg-neel-100 text-neel-700 dark:bg-neel-900/30 dark:text-neel-400' :
                      'bg-haldi-100 text-haldi-700 dark:bg-haldi-900/30 dark:text-haldi-300'
                    }`}>{u.role?.toUpperCase()}</span>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active === false ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">Disabled</span>
                    ) : u.locked_until ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">Locked</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Active</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-mitti-500 dark:text-mitti-400">{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}</td>
                  <td className="px-4 py-3">
                    <div className="flex space-x-1">
                      <button onClick={() => { setEditUser(u); setEditRole(u.role); }} title={t('admin.changeRole', 'Edit role')}
                        className="p-1.5 text-mitti-600 hover:bg-mitti-50 dark:hover:bg-mitti-900/20 rounded-lg"><BarChart3 className="w-4 h-4" /></button>
                      {u.locked_until && (
                        <button onClick={() => handleUnlock(u.id)} title="Unlock"
                          className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg"><Unlock className="w-4 h-4" /></button>
                      )}
                      {u.is_active !== false && (
                        <button onClick={() => handleDisable(u.id)} title="Disable"
                          className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"><Lock className="w-4 h-4" /></button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <p className="text-center py-8 text-mitti-500 dark:text-mitti-400">No users found.</p>}
      </div>

      {/* Edit Role Modal */}
      {editUser && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="village-card rounded-xl shadow-2xl w-full max-w-sm p-4 md:p-6">
            <h3 className="text-lg font-bold font-display text-mitti-900 dark:text-kora-100 mb-4">Edit User: {editUser.username}</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('admin.role', 'Role')}</label>
              <select value={editRole} onChange={(e) => setEditRole(e.target.value)}
                className="w-full px-3 py-2 village-input rounded-lg">
                <option value="citizen">Citizen</option>
                <option value="officer">Officer</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="flex justify-end space-x-3">
              <button onClick={() => setEditUser(null)} className="px-4 py-2 border border-mitti-200 dark:border-night-border rounded-lg text-mitti-700 dark:text-mitti-300">{t('common.cancel', 'Cancel')}</button>
              <button onClick={handleUpdateRole} className="px-4 py-2 btn-mitti rounded-lg font-medium">{t('common.save', 'Save')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* ===================== OFFICER CODES TAB ===================== */
const DEPARTMENTS = [
  'agriculture', 'education', 'health', 'finance', 'rural_development',
  'urban_development', 'water_resources', 'social_welfare', 'labour',
  'revenue', 'home', 'public_works', 'transport', 'general',
];

const OfficerCodesTab: React.FC = () => {
  const { t } = useTranslation();
  const [codes, setCodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [department, setDepartment] = useState('agriculture');
  const [designation, setDesignation] = useState('');
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => { loadCodes(); }, []);

  const loadCodes = async () => {
    setLoading(true);
    try {
      const data = await apiService.listOfficerCodes();
      setCodes(data.codes || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await apiService.generateOfficerCode(department, designation || undefined);
      setDesignation('');
      loadCodes();
    } catch { toast.error('Failed to generate code'); }
    finally { setGenerating(false); }
  };

  const handleCopy = async (code: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const getStatusBadge = (c: any) => {
    if (c.is_used) return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-mitti-100 text-mitti-600 dark:bg-night-card dark:text-mitti-400">{t('admin.used', 'Used')}</span>;
    if (c.expires_at && new Date(c.expires_at) < new Date()) return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">{t('admin.expired', 'Expired')}</span>;
    return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">{t('admin.available', 'Available')}</span>;
  };

  return (
    <div className="space-y-6">
      {/* Generate Form */}
      <div className="village-card rounded-xl p-6">
        <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4 flex items-center">
          <KeyRound className="w-5 h-5 mr-2 text-mitti-600" />{t('admin.generateCode', 'Generate Officer Registration Code')}
        </h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('admin.department', 'Department')} *</label>
            <select value={department} onChange={(e) => setDepartment(e.target.value)}
              className="w-full px-3 py-2 village-input rounded-lg text-sm">
              {DEPARTMENTS.map(d => <option key={d} value={d}>{d.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{t('admin.designation', 'Designation')} (optional)</label>
            <input type="text" value={designation} onChange={(e) => setDesignation(e.target.value)}
              placeholder="e.g., District Officer"
              className="w-full px-3 py-2 village-input rounded-lg text-sm" />
          </div>
          <button onClick={handleGenerate} disabled={generating}
            className="px-5 py-2 btn-mitti rounded-lg font-medium disabled:opacity-50 flex items-center space-x-2">
            {generating ? <ThemedSpinner /> : <Plus className="w-4 h-4" />}
            <span>{t('admin.generateButton', 'Generate Code')}</span>
          </button>
        </div>
      </div>

      {/* Codes Table */}
      {loading ? (
        <div className="text-center py-12"><ThemedSpinner /></div>
      ) : codes.length === 0 ? (
        <div className="village-card rounded-xl p-12 text-center">
          <KeyRound className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
          <p className="text-mitti-600 dark:text-mitti-400">{t('admin.noCodesYet', 'No officer codes generated yet.')}</p>
        </div>
      ) : (
        <div className="village-card rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-mitti-500 dark:text-mitti-400 bg-mitti-50/50 dark:bg-mitti-900/10">
                  <th className="px-4 py-3 font-medium">{t('admin.code', 'Code')}</th>
                  <th className="px-4 py-3 font-medium">{t('admin.department', 'Department')}</th>
                  <th className="px-4 py-3 font-medium">{t('admin.designation', 'Designation')}</th>
                  <th className="px-4 py-3 font-medium">{t('common.status', 'Status')}</th>
                  <th className="px-4 py-3 font-medium">{t('admin.usedBy', 'Used By')}</th>
                  <th className="px-4 py-3 font-medium">{t('admin.createdDate', 'Created')}</th>
                  <th className="px-4 py-3 font-medium">{t('common.actions', 'Actions')}</th>
                </tr>
              </thead>
              <tbody>
                {codes.map((c: any) => (
                  <tr key={c.id || c.code} className="border-t border-mitti-100 dark:border-night-border/50 hover:bg-mitti-50/30 dark:hover:bg-mitti-900/5">
                    <td className="px-4 py-3 font-mono font-bold text-mitti-600 dark:text-mitti-400">{c.code}</td>
                    <td className="px-4 py-3 text-mitti-700 dark:text-mitti-300 capitalize">{c.department?.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-mitti-600 dark:text-mitti-400">{c.designation || '-'}</td>
                    <td className="px-4 py-3">{getStatusBadge(c)}</td>
                    <td className="px-4 py-3 text-mitti-600 dark:text-mitti-400">{c.used_by_name || (c.used_by ? `User #${c.used_by}` : '-')}</td>
                    <td className="px-4 py-3 text-mitti-500 dark:text-mitti-400 text-xs">{c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td className="px-4 py-3">
                      {!c.is_used && (
                        <button onClick={() => handleCopy(c.code)} title="Copy code"
                          className="p-1.5 text-mitti-600 hover:bg-mitti-50 dark:hover:bg-mitti-900/20 rounded-lg">
                          {copiedCode === c.code ? <CheckCircle className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

/* ===================== AUDIT TAB ===================== */
const AuditTab: React.FC = () => {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const limit = 30;

  useEffect(() => { loadLogs(); }, [offset]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAuditLogs(limit, offset);
      setLogs(data.audit_logs || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const getActionColor = (action: string) => {
    if (action?.includes('login')) return 'bg-mitti-100 text-mitti-700 dark:bg-mitti-900/30 dark:text-mitti-400';
    if (action?.includes('create') || action?.includes('register')) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    if (action?.includes('delete')) return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    if (action?.includes('update')) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
    return 'bg-mitti-100 text-mitti-700 dark:bg-night-card dark:text-mitti-300';
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner /></div>;

  return (
    <div className="space-y-4">
      <div className="village-card rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-mitti-500 dark:text-mitti-400 bg-mitti-50/50 dark:bg-mitti-900/10">
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">{t('admin.username', 'User')}</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Resource</th>
                <th className="px-4 py-3 font-medium">{t('common.status', 'Status')}</th>
                <th className="px-4 py-3 font-medium">IP</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log: any, i: number) => (
                <tr key={log.id || i} className="border-t border-mitti-100 dark:border-night-border/50">
                  <td className="px-4 py-3 text-mitti-500 dark:text-mitti-400 whitespace-nowrap text-xs">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-4 py-3 font-medium text-mitti-900 dark:text-kora-100">{log.username || 'System'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getActionColor(log.action_type)}`}>
                      {log.action_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-mitti-600 dark:text-mitti-300">{log.resource_type || '-'}{log.resource_id ? ` #${log.resource_id}` : ''}</td>
                  <td className="px-4 py-3">
                    {log.status_code && log.status_code < 400 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : log.status_code ? (
                      <XCircle className="w-4 h-4 text-red-500" />
                    ) : '-'}
                  </td>
                  <td className="px-4 py-3 text-mitti-500 dark:text-mitti-400 text-xs font-mono">{log.ip_address || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {logs.length === 0 && <p className="text-center py-8 text-mitti-500 dark:text-mitti-400">No audit logs found.</p>}
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0}
          className="px-4 py-2 border border-mitti-200 dark:border-night-border rounded-lg text-sm text-mitti-700 dark:text-mitti-300 disabled:opacity-50 hover:bg-mitti-50 dark:hover:bg-mitti-900/20">Previous</button>
        <span className="text-sm text-mitti-500 dark:text-mitti-400">Showing {offset + 1} - {offset + logs.length}</span>
        <button onClick={() => setOffset(offset + limit)} disabled={logs.length < limit}
          className="px-4 py-2 border border-mitti-200 dark:border-night-border rounded-lg text-sm text-mitti-700 dark:text-mitti-300 disabled:opacity-50 hover:bg-mitti-50 dark:hover:bg-mitti-900/20">Next</button>
      </div>
    </div>
  );
};

/* ===================== SLA CONFIG TAB ===================== */
const SlaConfigTab: React.FC = () => {
  const [config, setConfig] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedDept, setExpandedDept] = useState<string | null>(null);

  useEffect(() => { loadConfig(); }, []);

  const loadConfig = async () => {
    try {
      const data = await apiService.getSlaConfig();
      setConfig(data.config || data.sla_config || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner /></div>;

  if (config.length === 0) return (
    <div className="village-card rounded-xl p-12 text-center">
      <Shield className="w-12 h-12 text-mitti-400 mx-auto mb-3" />
      <p className="text-mitti-600 dark:text-mitti-400">No SLA configurations found.</p>
    </div>
  );

  return (
    <div className="space-y-3">
      {config.map((c: any) => (
        <div key={c.department} className="village-card rounded-xl overflow-hidden">
          <div className="p-4 flex items-center justify-between cursor-pointer" onClick={() => setExpandedDept(expandedDept === c.department ? null : c.department)}>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-mitti-100 dark:bg-mitti-900/30 rounded-lg"><Shield className="w-5 h-5 text-mitti-600 dark:text-mitti-400" /></div>
              <span className="font-semibold text-mitti-900 dark:text-kora-100 capitalize">{c.department?.replace('_', ' ')}</span>
            </div>
            {expandedDept === c.department ? <ChevronUp className="w-5 h-5 text-mitti-400" /> : <ChevronDown className="w-5 h-5 text-mitti-400" />}
          </div>
          {expandedDept === c.department && (
            <div className="px-4 pb-4 border-t border-mitti-200 dark:border-night-border pt-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <p className="text-xs text-red-600 dark:text-red-400 font-semibold">Critical</p>
                  <p className="text-lg font-bold text-red-800 dark:text-red-300">{c.critical_sla_hours}h</p>
                </div>
                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                  <p className="text-xs text-orange-600 dark:text-orange-400 font-semibold">High</p>
                  <p className="text-lg font-bold text-orange-800 dark:text-orange-300">{c.high_sla_hours}h</p>
                </div>
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 font-semibold">Medium</p>
                  <p className="text-lg font-bold text-yellow-800 dark:text-yellow-300">{c.medium_sla_hours}h</p>
                </div>
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <p className="text-xs text-green-600 dark:text-green-400 font-semibold">Low</p>
                  <p className="text-lg font-bold text-green-800 dark:text-green-300">{c.low_sla_hours}h</p>
                </div>
              </div>
              <div className="mt-3 text-xs text-mitti-500 dark:text-mitti-400">
                Working hours: {c.working_hours_start || '09:00'} - {c.working_hours_end || '17:00'} | Weekends: {c.count_weekends ? 'Counted' : 'Excluded'}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

/* ===================== SYSTEM TAB ===================== */
const SystemTab: React.FC = () => {
  const { t } = useTranslation();
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  useEffect(() => { loadHealth(); }, []);

  const loadHealth = async () => {
    try {
      const data = await apiService.systemHealth();
      setHealth(data);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  const handleClearCache = async () => {
    setClearing(true);
    try {
      await apiService.clearCache();
      toast.success('Cache cleared successfully');
    } catch { toast.error('Failed to clear cache'); }
    finally { setClearing(false); }
  };

  if (loading) return <div className="text-center py-12"><ThemedSpinner /></div>;

  return (
    <div className="space-y-6">
      {/* Health Status */}
      <div className="village-card rounded-xl p-6">
        <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4">{t('admin.systemHealthTab', 'System Health')}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="village-card p-4 rounded-lg border border-green-200 dark:border-green-800">
            <div className="flex items-center space-x-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span className="font-semibold text-green-800 dark:text-green-300">API Server</span>
            </div>
            <p className="text-sm text-green-700 dark:text-green-400">{t('admin.systemOnline', 'Running')}</p>
          </div>
          <div className="village-card p-4 rounded-lg border border-green-200 dark:border-green-800">
            <div className="flex items-center space-x-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span className="font-semibold text-green-800 dark:text-green-300">Database</span>
            </div>
            <p className="text-sm text-green-700 dark:text-green-400">
              {health?.db_size ? `Size: ${(health.db_size / 1024 / 1024).toFixed(2)} MB` : 'Connected'}
            </p>
          </div>
          <div className={`village-card p-4 rounded-lg border ${health?.rag_status === 'ready' ? 'border-green-200 dark:border-green-800' : 'border-yellow-200 dark:border-yellow-800'}`}>
            <div className="flex items-center space-x-2 mb-2">
              {health?.rag_status === 'ready' ? <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" /> : <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />}
              <span className="font-semibold text-mitti-800 dark:text-mitti-200">RAG Engine</span>
            </div>
            <p className="text-sm text-mitti-700 dark:text-mitti-300">{health?.rag_status || 'Unknown'}</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="village-card rounded-xl p-6">
        <h2 className="text-lg font-semibold font-display text-mitti-900 dark:text-kora-100 mb-4">System Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleClearCache} disabled={clearing}
            className="px-4 py-2 btn-mitti rounded-lg font-medium disabled:bg-mitti-400 flex items-center space-x-2">
            {clearing ? <ThemedSpinner /> : null}
            <span>Clear Cache</span>
          </button>
          <button onClick={loadHealth}
            className="px-4 py-2 btn-neel rounded-lg font-medium flex items-center space-x-2">
            <span>Refresh Health</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
