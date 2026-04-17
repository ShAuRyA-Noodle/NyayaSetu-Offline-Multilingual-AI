import React, { useState, useEffect } from 'react';
import { Volume2, Radio, ChevronDown, ChevronUp, BookOpen, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import PageTransition from '../components/ui/PageTransition';
import AudioPlayer from '../components/nyayavaani/AudioPlayer';
import LanguageSelector from '../components/nyayavaani/LanguageSelector';
import apiService from '../services/api';

interface NyayaVaaniStatus {
  status: string;
  mode: string;
  sarvam_api: boolean;
  ollama_available: boolean;
  ollama_models: string[];
  supported_languages: number;
}

interface NyayaVaaniScheme {
  scheme_id: string;
  scheme_name: string;
  department: string;
  short_description: string;
}

const NyayaVaani: React.FC = () => {
  const { t } = useTranslation();
  const [systemStatus, setSystemStatus] = useState<NyayaVaaniStatus | null>(null);
  const [showSystemInfo, setShowSystemInfo] = useState(false);

  // Notices state
  const [notices, setNotices] = useState<any[]>([]);
  const [noticeLanguage, setNoticeLanguage] = useState('hi');

  // Schemes state
  const [schemes, setSchemes] = useState<NyayaVaaniScheme[]>([]);
  const [schemeLanguage, setSchemeLanguage] = useState('hi');
  const [schemesLoading, setSchemesLoading] = useState(false);

  useEffect(() => {
    loadStatus();
    loadPublicNotices();
    loadSchemes();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await apiService.nyayavaaniStatus();
      setSystemStatus(data);
    } catch (err) {
      console.warn('Failed to load NyayaVaani status:', err);
    }
  };

  const loadPublicNotices = async () => {
    try {
      const data = await apiService.getPublicNotices(10, 0);
      setNotices(data.notices || []);
    } catch (err) {
      console.warn('Failed to load notices:', err);
    }
  };

  const loadSchemes = async () => {
    setSchemesLoading(true);
    try {
      const data = await apiService.getNyayaVaaniSchemes();
      setSchemes(data.schemes || []);
    } catch (err) {
      console.warn('Failed to load NyayaVaani schemes:', err);
    } finally {
      setSchemesLoading(false);
    }
  };

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto p-4 sm:p-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-xl flex items-center justify-center shadow-mitti">
              <Radio className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold font-display text-kora-100 tracking-tight">{t('nyayavaani.title')}</h1>
              <p className="text-sm text-mitti-500/40">{t('nyayavaani.subtitle')}</p>
            </div>
            {systemStatus && (
              <span className={`ml-auto px-3 py-1 rounded-full text-xs font-medium ${
                systemStatus.mode === 'online'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              }`}>
                {systemStatus.mode === 'online' ? t('nyayavaani.online') : t('nyayavaani.offline')}
              </span>
            )}
          </div>
        </div>

        {/* Listen to Notices */}
        <div className="village-panel rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Volume2 className="w-5 h-5 text-mitti-500" />
              <h2 className="text-lg font-semibold text-kora-100">{t('nyayavaani.listenNotices')}</h2>
            </div>
            <LanguageSelector selected={noticeLanguage} onSelect={setNoticeLanguage} mode="dropdown" className="w-48" />
          </div>
          <p className="text-sm text-mitti-500 dark:text-mitti-400 mb-4">{t('nyayavaani.listenNoticesDesc')}</p>

          {notices.length === 0 ? (
            <div className="text-center py-8 text-mitti-400">
              <Volume2 size={40} className="mx-auto mb-2 opacity-30" />
              <p>{t('nyayavaani.noNotices')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {notices.map((notice: any) => (
                <div key={notice.notice_id} className="bg-mitti-50/50 dark:bg-night-card/50 rounded-xl p-4 border border-mitti-200/20 dark:border-night-border/20">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-medium text-kora-200 text-sm">{notice.subject}</h3>
                      <p className="text-xs text-mitti-500 mt-0.5">{notice.scheme_name} &middot; {notice.published_at?.split('T')[0]}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-mitti-100 text-mitti-700 dark:bg-mitti-900/30 dark:text-mitti-400">
                      {notice.notice_type}
                    </span>
                  </div>
                  <p className="text-xs text-mitti-600 dark:text-mitti-400 line-clamp-2 mb-3">{notice.body}</p>
                  <AudioPlayer
                    src={`/api/v1/nyayavaani/notice/${notice.notice_id}/audio?language=${noticeLanguage}`}
                    label={`${t('nyayavaani.playAudio')} - ${notice.subject}`}
                    compact
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Listen to Government Schemes */}
        <div className="village-panel rounded-2xl p-6 mt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-mitti-500" />
              <h2 className="text-lg font-semibold text-kora-100">
                {t('nyayavaani.listenSchemes', 'Listen to Government Schemes')}
              </h2>
            </div>
            <LanguageSelector selected={schemeLanguage} onSelect={setSchemeLanguage} mode="dropdown" className="w-48" />
          </div>
          <p className="text-sm text-mitti-500 dark:text-mitti-400 mb-4">
            {t('nyayavaani.listenSchemesDesc', 'Listen to detailed AI-generated summaries of government schemes in your language')}
          </p>

          {schemesLoading ? (
            <div className="flex items-center justify-center py-8 text-mitti-400">
              <Loader2 size={20} className="animate-spin mr-2" />
              <span className="text-sm">{t('common.loading', 'Loading...')}</span>
            </div>
          ) : schemes.length === 0 ? (
            <div className="text-center py-8 text-mitti-400">
              <BookOpen size={40} className="mx-auto mb-2 opacity-30" />
              <p>{t('nyayavaani.noSchemes', 'No schemes available')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {schemes.map((scheme) => (
                <div key={scheme.scheme_id} className="bg-mitti-50/50 dark:bg-night-card/50 rounded-xl p-4 border border-mitti-200/20 dark:border-night-border/20">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-medium text-kora-200 text-sm">{scheme.scheme_name}</h3>
                      <p className="text-xs text-mitti-500 mt-0.5">{scheme.department}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex-shrink-0 ml-2">
                      Active
                    </span>
                  </div>
                  {scheme.short_description && (
                    <p className="text-xs text-mitti-600 dark:text-mitti-400 line-clamp-2 mb-3">{scheme.short_description}</p>
                  )}
                  <AudioPlayer
                    src={`/api/v1/nyayavaani/scheme/${scheme.scheme_id}/audio?language=${schemeLanguage}`}
                    label={`${t('nyayavaani.playAudio', 'Play Audio')} - ${scheme.scheme_name}`}
                    compact
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* System Info (Collapsible) */}
        <div className="mt-6">
          <button
            onClick={() => setShowSystemInfo(!showSystemInfo)}
            className="flex items-center gap-2 text-sm text-mitti-500 hover:text-mitti-700 dark:hover:text-mitti-300 transition-colors"
          >
            {showSystemInfo ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {t('nyayavaani.systemStatus')}
          </button>
          <div
            style={{
              display: 'grid',
              gridTemplateRows: (showSystemInfo && systemStatus) ? '1fr' : '0fr',
              transition: 'grid-template-rows 0.28s cubic-bezier(0.25, 1, 0.5, 1)',
            }}
          >
            <div className="overflow-hidden">
              {systemStatus && (
              <div style={{ opacity: showSystemInfo ? 1 : 0, transition: 'opacity 0.2s ease' }}
                className="mt-2 bg-mitti-50/30 dark:bg-night-card/50 rounded-xl p-4 border border-mitti-200 dark:border-night-border"
              >
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <span className="text-mitti-500 text-xs block">Mode</span>
                    <span className="font-medium">{systemStatus.mode}</span>
                  </div>
                  <div>
                    <span className="text-mitti-500 text-xs block">Sarvam API</span>
                    <span className={systemStatus.sarvam_api ? 'text-green-500' : 'text-red-500'}>
                      {systemStatus.sarvam_api ? 'Connected' : 'Offline'}
                    </span>
                  </div>
                  <div>
                    <span className="text-mitti-500 text-xs block">Ollama</span>
                    <span className={systemStatus.ollama_available ? 'text-green-500' : 'text-red-500'}>
                      {systemStatus.ollama_available ? 'Available' : 'Offline'}
                    </span>
                  </div>
                  <div>
                    <span className="text-mitti-500 text-xs block">{t('nyayavaani.languages')}</span>
                    <span className="font-medium">{systemStatus.supported_languages}</span>
                  </div>
                </div>
                {systemStatus.ollama_models.length > 0 && (
                  <div className="mt-3">
                    <span className="text-mitti-500 text-xs block mb-1">Ollama Models</span>
                    <div className="flex flex-wrap gap-1">
                      {systemStatus.ollama_models.map((m, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 bg-mitti-100 dark:bg-night-card rounded">{m}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  );
};

export default NyayaVaani;
