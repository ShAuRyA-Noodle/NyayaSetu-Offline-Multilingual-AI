import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Loader2, AlertTriangle } from 'lucide-react';
import apiService from '../../services/api';

interface AudioPlayerProps {
  src: string;
  label?: string;
  compact?: boolean;
  className?: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ src, label, compact = false, className = '' }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8001';

  // Fetch the audio via the authenticated axios client and convert to a blob URL.
  // <audio src> cannot send Authorization headers; without this, every authed
  // audio fetch returns 401.
  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;

    const load = async () => {
      if (!src) return;
      setError(null);
      setLoading(true);

      // Build the path/url to fetch. axios is configured with baseURL = apiBase;
      // pass relative paths through, absolute http(s) urls as-is.
      const isAbsolute = /^https?:\/\//i.test(src);
      const requestUrl = isAbsolute ? src : src;

      try {
        const response = await apiService.client.get<Blob>(requestUrl, {
          responseType: 'blob',
          // For absolute URLs, override baseURL so axios doesn't prefix it.
          baseURL: isAbsolute ? undefined : apiBase,
          timeout: 60000,
        });

        if (cancelled) return;
        const url = URL.createObjectURL(response.data);
        createdUrl = url;
        setBlobUrl(url);
        setLoading(false);
      } catch (err: any) {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.error('AudioPlayer fetch failed:', err);
        setError(
          err?.response?.status === 401
            ? 'Authentication required'
            : 'Failed to load audio'
        );
        setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [src, apiBase]);

  // Revoke the blob URL on unmount / src change to avoid leaks
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
    };
    const onLoadedMetadata = () => {
      setDuration(audio.duration);
    };
    const onEnded = () => { setPlaying(false); setProgress(0); };
    const onPlayEvt = () => setPlaying(true);
    const onPauseEvt = () => setPlaying(false);
    const onErrorEvt = () => { setPlaying(false); setError('Playback failed'); };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('play', onPlayEvt);
    audio.addEventListener('pause', onPauseEvt);
    audio.addEventListener('error', onErrorEvt);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('play', onPlayEvt);
      audio.removeEventListener('pause', onPauseEvt);
      audio.removeEventListener('error', onErrorEvt);
    };
  }, [blobUrl]);

  // Reset state when src changes
  useEffect(() => {
    setPlaying(false);
    setProgress(0);
    setCurrentTime(0);
    setDuration(0);
  }, [src]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || !blobUrl) return;

    if (playing) {
      audio.pause();
    } else {
      // Pause other audio elements
      document.querySelectorAll('audio').forEach((a) => {
        if (a !== audio) a.pause();
      });
      audio.play().catch(() => {
        setError('Playback failed');
      });
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    audio.currentTime = pos * audio.duration;
  };

  const fmt = (s: number) => {
    if (!s || !isFinite(s)) return '0:00';
    return `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        {blobUrl && <audio ref={audioRef} src={blobUrl} preload="auto" />}
        <button
          onClick={togglePlay}
          disabled={loading || !!error || !blobUrl}
          aria-label={playing ? 'Pause audio' : 'Play audio'}
          className={`w-8 h-8 rounded-full ${
            error
              ? 'bg-red-400'
              : 'bg-gradient-to-br from-saffron-500 to-orange-500'
          } text-white flex items-center justify-center hover:shadow-md transition-shadow disabled:opacity-70`}
        >
          {loading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : error ? (
            <AlertTriangle size={14} />
          ) : playing ? (
            <Pause size={14} />
          ) : (
            <Play size={14} className="ml-0.5" />
          )}
        </button>
        <span className="text-xs text-gray-500">
          {loading ? 'Loading audio...' : error ? error : label || ''}
        </span>
      </div>
    );
  }

  return (
    <div className={`bg-white/50 dark:bg-white/5 rounded-xl p-3 border border-white/20 dark:border-white/10 ${className}`}>
      {blobUrl && <audio ref={audioRef} src={blobUrl} preload="auto" />}
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          disabled={loading || !!error || !blobUrl}
          aria-label={playing ? 'Pause audio' : 'Play audio'}
          className={`w-10 h-10 rounded-full ${
            error
              ? 'bg-red-400'
              : 'bg-gradient-to-br from-saffron-500 to-orange-500'
          } text-white flex items-center justify-center flex-shrink-0 hover:shadow-saffron transition-shadow disabled:opacity-70`}
        >
          {loading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : error ? (
            <AlertTriangle size={18} />
          ) : playing ? (
            <Pause size={18} />
          ) : (
            <Play size={18} className="ml-0.5" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          {label && (
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate mb-1">
              {loading ? 'Loading audio...' : error ? error : label}
            </p>
          )}
          <div
            className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer"
            onClick={handleSeek}
            role="slider"
            aria-label="Audio progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress)}
          >
            <div
              className="h-full bg-gradient-to-r from-saffron-500 to-orange-500 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-gray-400 font-mono">{fmt(currentTime)}</span>
            <span className="text-[10px] text-gray-400 font-mono">{fmt(duration)}</span>
          </div>
        </div>

        <Volume2 size={14} className="text-gray-400 flex-shrink-0" />
      </div>
    </div>
  );
};

export default AudioPlayer;
