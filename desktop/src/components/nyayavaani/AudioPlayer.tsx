import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Loader2 } from 'lucide-react';

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
  const [error, setError] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
    };
    const onLoadedMetadata = () => {
      setDuration(audio.duration);
      setLoading(false);
    };
    const onEnded = () => { setPlaying(false); setProgress(0); };
    const onCanPlay = () => setLoading(false);
    const onWaiting = () => { if (playing) setLoading(true); };
    const onError = () => { setLoading(false); setPlaying(false); setError(true); };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('canplay', onCanPlay);
    audio.addEventListener('waiting', onWaiting);
    audio.addEventListener('error', onError);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('canplay', onCanPlay);
      audio.removeEventListener('waiting', onWaiting);
      audio.removeEventListener('error', onError);
    };
  }, [src, playing]);

  // Reset state when src changes
  useEffect(() => {
    setPlaying(false);
    setLoading(false);
    setProgress(0);
    setCurrentTime(0);
    setDuration(0);
    setError(false);
  }, [src]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (playing) {
      audio.pause();
      setPlaying(false);
      setLoading(false);
    } else {
      setError(false);
      // Pause other audio elements
      document.querySelectorAll('audio').forEach((a) => {
        if (a !== audio) a.pause();
      });
      setLoading(true);
      audio.play().then(() => {
        setPlaying(true);
      }).catch(() => {
        setLoading(false);
        setError(true);
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

  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const fullSrc = src.startsWith('http') ? src : `${apiBase}${src}`;

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <audio ref={audioRef} src={fullSrc} preload="none" />
        <button
          onClick={togglePlay}
          disabled={loading}
          className={`w-8 h-8 rounded-full ${
            error
              ? 'bg-red-400'
              : 'bg-gradient-to-br from-saffron-500 to-orange-500'
          } text-white flex items-center justify-center hover:shadow-md transition-shadow disabled:opacity-70`}
        >
          {loading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : playing ? (
            <Pause size={14} />
          ) : (
            <Play size={14} className="ml-0.5" />
          )}
        </button>
        <span className="text-xs text-gray-500">
          {loading ? 'Generating audio...' : error ? 'Failed to load' : label || ''}
        </span>
      </div>
    );
  }

  return (
    <div className={`bg-white/50 dark:bg-white/5 rounded-xl p-3 border border-white/20 dark:border-white/10 ${className}`}>
      <audio ref={audioRef} src={fullSrc} preload="none" />
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          disabled={loading}
          className={`w-10 h-10 rounded-full ${
            error
              ? 'bg-red-400'
              : 'bg-gradient-to-br from-saffron-500 to-orange-500'
          } text-white flex items-center justify-center flex-shrink-0 hover:shadow-saffron transition-shadow disabled:opacity-70`}
        >
          {loading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : playing ? (
            <Pause size={18} />
          ) : (
            <Play size={18} className="ml-0.5" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          {label && (
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate mb-1">
              {loading ? 'Generating audio...' : error ? 'Failed to load audio' : label}
            </p>
          )}
          <div
            className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer"
            onClick={handleSeek}
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
